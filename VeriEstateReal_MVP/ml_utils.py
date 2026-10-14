"""Feature engineering and explainable checks for VeriEstateReal."""
import re
from difflib import SequenceMatcher
import pandas as pd
FEATURE_NAMES = ["address_similarity","locality_match","city_match","property_type_match","area_relative_difference","both_ids_present","property_id_match","description_similarity"]
def normalize(value):
    value = "" if value is None else str(value)
    value = value.lower().strip()
    for old,new in [(r"\broad\b","rd"),(r"\bstreet\b","st"),(r"\bavenue\b","ave"),(r"\bapartment\b","apt")]: value=re.sub(old,new,value)
    return " ".join(re.sub(r"[^a-z0-9]+"," ",value).split())
def similarity(a,b):
    a,b=normalize(a),normalize(b)
    return round(SequenceMatcher(None,a,b).ratio(),5) if a and b else 0.0
def num(v):
    try: return float(str(v).replace(",","").strip()) if v not in (None,"") else None
    except (ValueError,TypeError): return None
def pair_features(a,b):
    aid,bid=normalize(a.get("property_id")),normalize(b.get("property_id"))
    aa,ba=num(a.get("area_sqft")),num(b.get("area_sqft"))
    diff=min(abs(aa-ba)/max(aa,ba),5.0) if aa and ba and max(aa,ba)>0 else 1.0
    return [similarity(a.get("address"),b.get("address")),float(bool(normalize(a.get("locality"))) and normalize(a.get("locality"))==normalize(b.get("locality"))),float(bool(normalize(a.get("city"))) and normalize(a.get("city"))==normalize(b.get("city"))),float(bool(normalize(a.get("property_type"))) and normalize(a.get("property_type"))==normalize(b.get("property_type"))),round(diff,5),float(bool(aid) and bool(bid)),float(bool(aid) and bool(bid) and aid==bid),similarity(a.get("description"),b.get("description"))]
def check_rule_mismatches(a,b):
    notes=[]
    for key,label in [("city","City"),("locality","Locality"),("property_type","Property type")]:
        av,bv=normalize(a.get(key)),normalize(b.get(key))
        if av and bv and av!=bv: notes.append(f"{label} differs between the two listings.")
    aid,bid=normalize(a.get("property_id")),normalize(b.get("property_id"))
    if aid and bid and aid!=bid: notes.append("Both listings have identifiers, but the identifiers differ.")
    aa,ba=num(a.get("area_sqft")),num(b.get("area_sqft"))
    if aa and ba and max(aa,ba)>0:
        pct=abs(aa-ba)/max(aa,ba)*100
        if pct>10: notes.append(f"Area differs by approximately {pct:.1f}%.")
    if similarity(a.get("address"),b.get("address"))<.45: notes.append("Address text has low similarity; check whether records refer to the same property.")
    return notes
def score_pair(model,a,b,threshold=.55):
    if model is None: raise RuntimeError("ML model missing. Run: python train_model.py")
    features=pair_features(a,b)
    probs=model.predict_proba(pd.DataFrame([features], columns=FEATURE_NAMES))[0]
    classes=list(model.classes_)
    score=float(probs[classes.index(1)])
    return {"features":dict(zip(FEATURE_NAMES,features)),"probability":score,"candidate":score>=threshold,"threshold":threshold,"warnings":check_rule_mismatches(a,b)}

