import streamlit as st
from datetime import datetime, date
import traceback
import pandas as pd  # Yeni eklendi
import analysis as anls  # Yeni oluşturduğun analiz dosyası

from api import (
    get_tgt, get_organizations, get_uevcb_list,
    get_entso_organizations, get_kudüp, get_kgüp, get_uevm,
    items_to_series,
)
from cache import load_cache, save_cache, cache_info
from excel_writer import build_excel

# ── SAYFA AYARI ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="EPİAŞ Veri İndirici",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ EPİAŞ Veri İndirici")
st.caption("KUDÜP · KGÜP · UEVM — Toplu Excel İndirme")

# ── SESSION STATE BAŞLANGICI ──────────────────────────────────────────────────

if "tgt"          not in st.session_state: st.session_state.tgt          = None
if "facilities"   not in st.session_state: st.session_state.facilities   = {}  # label -> [org_id, uevcb_id, name]
if "selected"     not in st.session_state: st.session_state.selected     = {}  # label -> [org_id, uevcb_id, name]
if "excel_bytes"  not in st.session_state: st.session_state.excel_bytes  = None
if "excel_fname"  not in st.session_state: st.session_state.excel_fname  = ""
if "cache_loaded" not in st.session_state: st.session_state.cache_loaded = False

def fmt(dt: date) -> str:
    return datetime(dt.year, dt.month, dt.day).strftime("%Y-%m-%dT00:00:00+03:00")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Giriş & Ayarlar
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("🔐 EPİAŞ Giriş")
    username = st.text_input("E-posta", placeholder="kullanici@epias.com.tr")
    password = st.text_input("Şifre", type="password")

    if st.button("🔑 Giriş Yap / TGT Yenile", use_container_width=True):
        if not username or not password:
            st.error("E-posta ve şifre boş olamaz.")
        else:
            with st.spinner("TGT alınıyor..."):
                try:
                    tgt = get_tgt(username, password)
                    st.session_state.tgt = tgt
                    st.success("✅ Giriş başarılı")
                except Exception as e:
                    st.error(f"❌ {e}")

    st.divider()
    st.header("📅 Tarih Aralığı")
    today      = date.today()
    start_date = st.date_input("Başlangıç", value=today.replace(day=1))
    end_date   = st.date_input("Bitiş",     value=today)

    if start_date > end_date:
        st.warning("⚠️ Başlangıç tarihi bitiş tarihinden büyük olamaz.")

    st.divider()

    # ── Tesis Listesi Cache ────────────────────────────────────────
    st.header("📦 Tesis Veritabanı")
    # app.py Sidebar içindeki "st.header("📦 Tesis Veritabanı")" satırından sonrasına:

    if st.session_state.facilities:
        if st.checkbox("🎯 Sadece RES'leri Listele", help="İçinde RES geçen tesisleri süzer"):
            # Orijinal listeyi bozmamak için geçici bir değişkende filtrele
            filtered_fac = anls.filter_only_res(st.session_state.facilities)
            display_facilities = filtered_fac
        else:
            display_facilities = st.session_state.facilities
    else:
        display_facilities = {}

    cached = load_cache()
    if cached and not st.session_state.cache_loaded:
        st.session_state.facilities   = {k: tuple(v) for k, v in cached["facilities"].items()}
        st.session_state.cache_loaded = True

    if st.session_state.facilities:
        cached_data = load_cache()
        info = cache_info(cached_data) if cached_data else f"{len(st.session_state.facilities)} tesis (bu oturum)"
        st.success(f"✅ {info}")
    else:
        st.info("Henüz tesis listesi yüklenmedi.")

    if st.button("🔄 Tesis Listesini Yenile", use_container_width=True,
                 help="EPİAŞ'tan tüm tesisleri çeker ve diske kaydeder (~2-5 dk)"):
        if not st.session_state.tgt:
            st.error("Önce giriş yapın.")
        else:
            tgt   = st.session_state.tgt
            start = fmt(start_date)
            end   = fmt(end_date)
            progress = st.progress(0, text="Organizasyonlar alınıyor...")
            try:
                orgs = get_organizations(start, end, tgt)
                all_fac = {}
                for i, org in enumerate(orgs):
                    oid = org["organizationId"]
                    try:
                        uevcbs = get_uevcb_list(oid, start, tgt)
                        for u in uevcbs:
                            label = u["name"]
                            if label in all_fac:
                                label = f"{u['name']} (org:{oid})"
                            all_fac[label] = (oid, u["id"], u["name"])
                    except Exception:
                        pass
                    pct = int((i + 1) / len(orgs) * 100)
                    progress.progress(pct, text=f"{i+1}/{len(orgs)} org işlendi...")

                save_cache({k: list(v) for k, v in all_fac.items()})
                st.session_state.facilities = all_fac
                progress.empty()
                st.success(f"✅ {len(all_fac)} tesis yüklendi ve kaydedildi.")
                st.rerun()
            except Exception as e:
                progress.empty()
                st.error(f"❌ {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# ANA ALAN — Tesis Arama & Seçim
# ═══════════════════════════════════════════════════════════════════════════════

col_search, col_selected = st.columns([1, 1], gap="large")

# ── Sol: Arama ─────────────────────────────────────────────────────────────────
with col_search:
    st.subheader("🔍 Tesis Ara")

    if not st.session_state.facilities:
        st.warning("Sol panelden önce tesis listesini yükleyin.")
    else:
        keyword = st.text_input(
            "Tesis adı yazın",
            placeholder="örn: ADA, RÜZGAR, GÜNEŞ, HES ...",
            key="search_input",
        )

        if keyword and len(keyword) >= 2:
            kw    = keyword.strip().upper()
            hits = [lbl for lbl in display_facilities if kw in lbl.upper()][:60]

            if hits:
                st.caption(f"{len(hits)} sonuç bulundu — seçip 'Ekle' butonuna bas")
                chosen = st.multiselect(
                    "Sonuçlar",
                    options=hits,
                    label_visibility="collapsed",
                    key="search_results",
                )
                if st.button("➕ Seçilenleri Ekle", use_container_width=True, type="primary"):
                    for lbl in chosen:
                        if lbl not in st.session_state.selected:
                            st.session_state.selected[lbl] = st.session_state.facilities[lbl]
                    st.rerun()
            else:
                st.info("Sonuç bulunamadı.")
        elif keyword:
            st.caption("En az 2 karakter girin.")

# ── Sağ: Seçili tesisler ───────────────────────────────────────────────────────
with col_selected:
    st.subheader(f"✅ Seçili Tesisler ({len(st.session_state.selected)})")

    if not st.session_state.selected:
        st.info("Henüz tesis eklenmedi.")
    else:
        to_remove = []
        for lbl in list(st.session_state.selected.keys()):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"• {lbl}")
            if c2.button("✕", key=f"rm_{lbl}", help="Kaldır"):
                to_remove.append(lbl)

        if to_remove:
            for lbl in to_remove:
                del st.session_state.selected[lbl]
            st.rerun()

        if st.button("🗑️ Tümünü Temizle", use_container_width=True):
            st.session_state.selected = {}
            st.session_state.excel_bytes = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# VERİ ÇEKİMİ & İNDİRME
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()

col_run, col_dl = st.columns([1, 1], gap="large")

with col_run:
    run_disabled = (
        not st.session_state.tgt
        or not st.session_state.selected
        or start_date > end_date
    )
    if st.button(
        "⬇️  Veriyi Çek & Excel Oluştur",
        disabled=run_disabled,
        use_container_width=True,
        type="primary",
    ):
        tgt      = st.session_state.tgt
        selected = st.session_state.selected
        start    = fmt(start_date)
        end      = fmt(end_date)

        log      = st.empty()
        progress = st.progress(0)
        total    = len(selected)

        try:
            log.info("📡 ENTSO organizasyon listesi alınıyor...")
            entso_items = get_entso_organizations(start, tgt)
            entso_map   = {
                it["organizationName"].strip().upper(): it["organizationId"]
                for it in entso_items
            }

            all_time_keys = set()
            facility_data = {}

            for i, (lbl, (org_id, uevcb_id, tesis_name)) in enumerate(selected.items()):
                log.info(f"🏭 {tesis_name} işleniyor... ({i+1}/{total})")

                kudüp_s = items_to_series(
                    get_kudüp(org_id, uevcb_id, start, end, tgt), "toplam")
                kgüp_s  = items_to_series(
                    get_kgüp(org_id, uevcb_id, start, end, tgt), "toplam")

                norm  = tesis_name.strip().upper()
                pp_id = entso_map.get(norm)
                if pp_id is None:
                    hits = [k for k in entso_map if norm in k or k in norm]
                    if hits:
                        pp_id = entso_map[hits[0]]

                uevm_s = {}
                if pp_id:
                    uevm_s = items_to_series(
                        get_uevm(pp_id, start, end, tgt), "total")

                facility_data[tesis_name] = {
                    "kudüp": kudüp_s,
                    "kgüp":  kgüp_s,
                    "uevm":  uevm_s,
                }
                all_time_keys.update(kudüp_s.keys())
                all_time_keys.update(kgüp_s.keys())
                all_time_keys.update(uevm_s.keys())
                progress.progress((i + 1) / total)

            log.empty()
            progress.empty()

            time_index = sorted(all_time_keys)
            excel_bytes = build_excel(facility_data, time_index)
            fname = (f"epias_{start_date.strftime('%Y%m%d')}"
                     f"_{end_date.strftime('%Y%m%d')}.xlsx")

            st.session_state.excel_bytes = excel_bytes
            st.session_state.excel_fname = fname
            st.success(f"✅ Excel hazır — {len(facility_data)} tesis, {len(time_index)} satır")
            # app.py içinde "st.success(f"✅ Excel hazır...")" satırının hemen altına:

            st.divider()
            st.subheader("📊 Portföy Analizi (Sapma Optimizasyonu)")
            
            try:
                with st.spinner("Matematiksel analiz yapılıyor..."):
                    # 1. 744 Saatlik Matrisi Oluştur
                    df_sapma = anls.create_imbalance_matrix(facility_data, time_index)
                    
                    # 2. Analizi Çalıştır
                    direction, pairs, corr = anls.find_portfolio_pairs(df_sapma)
                    
                    # 3. Görselleştirme - Tablar
                    tab1, tab2, tab3 = st.tabs(["📈 Sapma Grafiği", "🤝 Eşleşmeler", "📉 Korelasyon"])
                    
                    with tab1:
                        st.line_chart(df_sapma)
                        st.caption("Pozitif değerler sistem fazlası, negatifler sistem açığıdır.")
                        
                    with tab2:
                        c1, c2 = st.columns(2)
                        c1.write("### Tesis Yönleri")
                        c1.dataframe(direction.rename("Ağırlıklı Yön"))
                        
                        c2.write("### Önerilen Eşleşmeler")
                        if not pairs:
                            c2.warning("Zıt yönlü sapan tesis bulunamadı.")
                        for p in pairs:
                            c2.success(f"**{p[0]}** & **{p[1]}**\n\nZıtlık (Korelasyon): {p[2]:.2f}")
                            
                    with tab3:
                        st.write("Tesislerin birbirine olan etkisi (-1 tam zıt, +1 aynı yön)")
                        st.dataframe(corr.style.background_gradient(cmap='RdBu_r', axis=None))

except Exception as e:
    st.error(f"Analiz sırasında bir hata oluştu: {e}")

        except Exception as e:
            log.empty()
            progress.empty()
            st.error(f"❌ Hata: {e}")
            st.code(traceback.format_exc())

with col_dl:
    if st.session_state.excel_bytes:
        st.download_button(
            label="📥 Excel İndir",
            data=st.session_state.excel_bytes,
            file_name=st.session_state.excel_fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
