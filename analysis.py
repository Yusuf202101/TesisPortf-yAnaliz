import pandas as pd
import numpy as np

def create_imbalance_matrix(facility_data, time_index):
    """744 saatlik Sapma (UEVM - KUDÜP) matrisi oluşturur."""
    data = {}
    for tesis, values in facility_data.items():
        # Saatlik serileri oluştur (Eksik veri varsa 0 kabul et)
        kudup = pd.Series(values['kudüp'], index=time_index)
        uevm = pd.Series(values['uevm'], index=time_index)
        
        # Sapma = Gerçekleşen Üretim - Verilen Program
        data[tesis] = uevm.fillna(0) - kudup.fillna(0)
    
    return pd.DataFrame(data)

def find_portfolio_pairs(df_sapma):
    """Negatif ve Pozitif sapanları bulur ve eşleştirir."""
    # Her tesisin toplam sapma yönü (Pozitif mi Negatif mi?)
    direction = df_sapma.sum().apply(lambda x: 'Pozitif' if x > 0 else 'Negatif')
    
    # Korelasyon matrisi: Birbirine zıt (negatif korelasyon) çalışanları bulmak için
    corr_matrix = df_sapma.corr()
    
    # Portföy Önerisi: Negatif korelasyonu (zıtlığı) en yüksek çiftler
    # -1'e en yakın olanlar birbirini en iyi sönümler (hedging)
    pairs = []
    # Basit mantık: Her negatif sapan için en zıt çalışan pozitif sapanı bul
    negatives = direction[direction == 'Negatif'].index
    positives = direction[direction == 'Pozitif'].index
    
    for neg in negatives:
        if len(positives) > 0:
            # En düşük korelasyona sahip pozitif tesisi bul
            best_match = corr_matrix[neg][positives].idxmin()
            score = corr_matrix[neg][best_match]
            pairs.append((neg, best_match, score))
            
    return direction, pairs, corr_matrix
