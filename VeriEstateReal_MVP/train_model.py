"""Train/evaluate a duplicate-candidate demo using synthetic listing pairs only."""
import json, random, re
from copy import deepcopy
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from joblib import dump
from ml_utils import pair_features, FEATURE_NAMES, similarity
ROOT=Path(__file__).resolve().parent
LOCALITIES=["Gotri","Alkapuri","Karelibaug","Manjalpur","Sevasi","Akota","Vesu","Adajan"]
CITIES=["Vadodara","Surat","Vapi","Bhubaneswar"]
TYPES=["Apartment","Villa","Plot","Independent House"]
STREETS=["Lake View Road","Green Park Road","Riverfront Avenue","Orchid Street","Palm Road","Sunrise Avenue","Garden Lane","Hill View Road"]
BUILDINGS=["Sunrise Residency","Green Heights","Palm Court","Lakeview Enclave","Orchid Towers","Riverfront Homes"]
def make_listings(n=520,seed=91):
    r=random.Random(seed); rows=[]
    for i in range(n):
        typ=r.choice(TYPES); ranges={"Apartment":(450,2200),"Villa":(1000,4500),"Plot":(600,5000),"Independent House":(700,3500)}; lo,hi=ranges[typ]
        num=r.randint(1,240); street=r.choice(STREETS); building=r.choice(BUILDINGS); unit=r.randint(101,1205); loc=r.choice(LOCALITIES); city=r.choice(CITIES)
        address=(f"Plot {num}, {street}" if typ=="Plot" else f"Flat {unit}, {building}, {street}" if typ=="Apartment" else f"Villa {num}, {building}, {street}" if typ=="Villa" else f"House {num}, {street}")
        rows.append({"address":address,"locality":loc,"city":city,"property_type":typ,"area_sqft":r.randint(lo,hi),"property_id":f"SYN-{i+1:05d}","description":f"{typ} in {loc}, {city}; {building}; {street}; about {r.randint(1,4)} bedrooms","entity":i})
    return rows
def variant(base,r):
    """Create another representation of same synthetic property, with varied fields."""
    v=deepcopy(base); address=v["address"]
    # Real listings may omit unit/plot prefixes or use reordered address parts.
    parts=[part.strip() for part in address.split(",") if part.strip()]
    choice=r.random()
    if len(parts)>=2 and choice < .25:
        address=", ".join(parts[1:])
    elif len(parts)>=2 and choice < .42:
        address=", ".join(parts[1:]+parts[:1])
    else:
        for old,new in [("Road","Rd."),("Avenue","Ave."),("Street","St."),("Apartment","Apt."),("Lakeview","Lake View")]:
            if old.lower() in address.lower() and r.random()<.70:
                address=re.sub(re.escape(old),new,address,flags=re.I)
        if r.random()<.35: address=address.replace(",", "")
    v["address"]=address
    # In real duplicates, identifiers can be missing or inconsistently entered.
    id_case=r.random()
    if id_case<.40: v["property_id"]=""
    elif id_case<.65: v["property_id"]=f"ALT-{r.randint(1000,9999)}"
    v["area_sqft"]=max(1,round(float(v["area_sqft"])*r.uniform(.94,1.06)))
    if r.random()<.50: v["description"]=f"{v['property_type']} in {v['locality']} area, {v['city']}"
    v.pop("entity",None)
    return v

def make_negative_pair(pool,r):
    """Sample harder non-duplicates, often sharing broad attributes."""
    for _ in range(120):
        a,b=r.sample(pool,2)
        area_diff=abs(float(a["area_sqft"])-float(b["area_sqft"]))/max(float(a["area_sqft"]),float(b["area_sqft"]),1)
        if (a["entity"] != b["entity"] and a["locality"]==b["locality"] and a["city"]==b["city"] and a["property_type"]==b["property_type"] and area_diff < 0.14 and similarity(a["address"],b["address"]) > 0.50):
            return a,b
    return r.sample(pool,2)

def pairs(pool,n,seed):
    r=random.Random(seed); X=[]; y=[]
    for _ in range(n//2):
        base=r.choice(pool); other=variant(base,r)
        X.append(pair_features(base,other)); y.append(1)
    for _ in range(n-len(y)):
        a,b=make_negative_pair(pool,r)
        X.append(pair_features(a,b)); y.append(0)
    ix=list(range(len(y))); r.shuffle(ix)
    return [X[i] for i in ix],[y[i] for i in ix]

def baseline_predict(features):
    """Transparent heuristic baseline: address/locality/type signals only."""
    names={name:i for i,name in enumerate(FEATURE_NAMES)}
    return [int(row[names["address_similarity"]] >= .78 and row[names["locality_match"]] == 1 and row[names["property_type_match"]] == 1) for row in features]

def main():
    ROOT.joinpath('models').mkdir(exist_ok=True); ROOT.joinpath('data').mkdir(exist_ok=True)
    listings=make_listings(); random.Random(123).shuffle(listings); cut=int(len(listings)*.7); train_pool,test_pool=listings[:cut],listings[cut:]
    Xtr,ytr=pairs(train_pool,1800,321); Xte,yte=pairs(test_pool,600,654)
    model=RandomForestClassifier(n_estimators=140,max_depth=12,min_samples_leaf=2,class_weight='balanced_subsample',random_state=42)
    model.fit(pd.DataFrame(Xtr,columns=FEATURE_NAMES),ytr); pred=model.predict(pd.DataFrame(Xte,columns=FEATURE_NAMES))
    baseline_pred=baseline_predict(Xte)
    metrics={"data_note":"SYNTHETIC DEMONSTRATION ONLY — not a real-world performance estimate.","train_pairs":len(Xtr),"test_pairs":len(Xte),"test_positive_pairs":int(sum(yte)),"accuracy":round(float(accuracy_score(yte,pred)),4),"precision_duplicate":round(float(precision_score(yte,pred,zero_division=0)),4),"recall_duplicate":round(float(recall_score(yte,pred,zero_division=0)),4),"f1_duplicate":round(float(f1_score(yte,pred,zero_division=0)),4),"confusion_matrix_labels_0_then_1":confusion_matrix(yte,pred,labels=[0,1]).tolist(),"feature_names":FEATURE_NAMES,"model":"RandomForestClassifier","baseline_accuracy":round(float(accuracy_score(yte,baseline_pred)),4),"baseline_precision_duplicate":round(float(precision_score(yte,baseline_pred,zero_division=0)),4),"baseline_recall_duplicate":round(float(recall_score(yte,baseline_pred,zero_division=0)),4),"baseline_f1_duplicate":round(float(f1_score(yte,baseline_pred,zero_division=0)),4),"class_balance_note":"The synthetic test set is deliberately balanced for demonstration; real-world duplicate prevalence will differ."}
    dump(model,ROOT/'models'/'duplicate_model.joblib')
    (ROOT/'models'/'model_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    pd.DataFrame(Xte,columns=FEATURE_NAMES).assign(label=yte,prediction=pred).to_csv(ROOT/'data'/'synthetic_test_predictions.csv',index=False)
    print(json.dumps(metrics,indent=2)); print("\nWARNING: these metrics are only for generated synthetic data, not real property listings.")
if __name__=='__main__': main()

