"""Rebuild the defensible aggregate evidence for revised Paper5."""
from pathlib import Path
import argparse, hashlib, json, re, sqlite3, struct, unicodedata
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.collections import PatchCollection

P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--clean-authorities',type=Path,required=True)
ap.add_argument('--raw-authorities',type=Path,required=True)
ap.add_argument('--legacy-tables',type=Path,required=True)
ap.add_argument('--output-dir',type=Path,default=P/'analysis')
ap.add_argument('--ward-geojson',type=Path,help='Former Thu Duc ward boundaries (GeoJSON).')
ap.add_argument('--vietnam-geojson',type=Path,help='Vietnam outline for the locator inset (GeoJSON).')
ap.add_argument('--poi-gpkg',type=Path,help='OSM point layer in GeoPackage format (EPSG:4326 point geometries).')
args=ap.parse_args();OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)

clean=pd.read_excel(args.clean_authorities,sheet_name='Data').dropna(how='all')
raw=pd.read_excel(args.raw_authorities).dropna(subset=['Timestamp'])
assert len(clean)==23 and clean.Timestamp.is_unique and raw.Timestamp.is_unique
assert clean.Timestamp.isin(raw.Timestamp).all()
raw=raw.set_index('Timestamp')
checks={}
for code,prefix in [('Q1.7','Q1.7 '),('Q1.8','Q1.8 '),('Q3.1','Q3.1 '),('Q3.6','Q3.6 ')]:
    col=next(c for c in raw.columns if c.startswith(prefix))
    a=clean[code].fillna('').astype(str).str.strip().values
    b=raw.loc[clean.Timestamp,col].fillna('').astype(str).str.strip().values
    checks[code]={'matched':int((a==b).sum()),'different':int((a!=b).sum())}
    assert (a==b).all()

def norm_role(x):
    x=str(x).strip().lower()
    if 'chuyên viên' in x:return 'Technical officer'
    if 'trưởng / phó phòng' in x or 'pho phong' in x:return 'Division head or deputy'
    if 'giám đốc' in x:return 'Unit director or deputy'
    if 'phó chủ tịch' in x:return 'District vice-chair'
    if 'viên chức' in x:return 'Public employee'
    if 'tổ trưởng' in x:return 'Team leader or deputy'
    return 'Other or unclear'
sample=clean.assign(role=clean['Q1.8'].map(norm_role)).role.value_counts().rename_axis('Recorded position').reset_index(name='n')
sample['share_%']=100*sample.n/len(clean);sample.to_csv(OUT/'sample_positions.csv',index=False)

labels={'Q3.1':'Waste sorting','Q3.2':'Water supply and drainage','Q3.3':'Public lighting','Q3.4':'Road quality','Q3.5':'Public activity space','Q3.6':'Health-care facilities'}
rows=[]
for code,label in labels.items():
    v=clean[code].fillna('').astype(str).str.strip()
    pos=v.eq('Đồng ý').sum()+v.eq('Hoàn toàn đồng ý').sum()
    neutral=v.eq('Không ý kiến').sum()
    neg=len(v)-pos-neutral
    rows.append({'item':code,'condition':label,'positive_n':int(pos),'no_opinion_n':int(neutral),'negative_n':int(neg),'positive_%':100*pos/len(v),'no_opinion_%':100*neutral/len(v),'negative_%':100*neg/len(v)})
local=pd.DataFrame(rows);local.to_csv(OUT/'local_assessment.csv',index=False)

before=pd.read_csv(args.legacy_tables/'table13b_wards_before.csv')
after=pd.read_csv(args.legacy_tables/'table13_wards_after.csv')
osm=pd.read_csv(args.legacy_tables/'table18_osm_stock.csv')
snap=pd.read_csv(args.legacy_tables/'table18b_osm_2026_snapshots.csv')
for name,d in [('wards_before',before),('wards_after',after),('osm_exposure',osm),('osm_snapshots_2026',snap)]:d.to_csv(OUT/(name+'.csv'),index=False)
rescale={'wards_before':len(before),'wards_after':len(after),'median_population_before':float(before.Pop_2025.median()),'median_population_after':float(after.Pop_2025.median()),'population_ratio':float(after.Pop_2025.median()/before.Pop_2025.median()),'median_area_before':float(before.area_km2.median()),'median_area_after':float(after.Area_km2.median()),'area_ratio':float(after.Area_km2.median()/before.area_km2.median())}

plt.rcParams.update({'font.family':'Arial','font.size':10})
navy='#244363';orange='#d4741c';teal='#347f78';grey='#9aa0aa';light='#d9dde3'
fig,ax=plt.subplots(1,2,figsize=(10.5,4.2))
metrics=['Median population','Median area']
ratios=[rescale['population_ratio'],rescale['area_ratio']]
ax[0].bar(metrics,[1,1],color=grey,label='Before (34 wards)');ax[0].bar(metrics,ratios,color=navy,alpha=.92,label='After (12 wards)')
for i,v in enumerate(ratios):ax[0].text(i,v+.08,f'{v:.2f}x',ha='center',fontweight='bold')
ax[0].set_ylabel('Index, median before = 1');ax[0].set_title('(a) Administrative unit size');ax[0].legend(frameon=False)
o=osm.sort_values('Ratio',ascending=True)
ax[1].barh(o['Object class'],o.Ratio,color=navy);ax[1].axvline(1,color='black',lw=1)
for i,v in enumerate(o.Ratio):ax[1].text(v+.06,i,f'{v:.2f}x',va='center')
ax[1].set_xlabel('Median after / median before');ax[1].set_title('(b) Mapped-object exposure per ward')
for a in ax:a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.2);a.set_axisbelow(True)
fig.tight_layout();fig.savefig(OUT/'Figure1_rescaling.png',dpi=300);plt.close(fig)

fig,ax=plt.subplots(figsize=(8.6,4.5));y=np.arange(len(local));
ax.barh(y,local['positive_%'],color=teal,label='Positive');ax.barh(y,local['no_opinion_%'],left=local['positive_%'],color=light,label='No opinion');ax.barh(y,local['negative_%'],left=local['positive_%']+local['no_opinion_%'],color=orange,label='Negative')
ax.set_yticks(y,local.condition);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Share of 23 source-linked respondents (%)');ax.legend(ncol=3,frameon=False,loc='lower center',bbox_to_anchor=(.5,-.28));ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'Figure2_local_assessment.png',dpi=300,bbox_inches='tight');plt.close(fig)

domain_map={
    'UBND / Hành chính':('Office of the People’s Council and People’s Committee','Ward'),
    'Quản lý đô thị':('Office of Economy, Infrastructure and Urban Affairs','Ward'),
    'Tài nguyên môi trường':('Office of Economy, Infrastructure and Urban Affairs','Ward'),
    'Kinh doanh':('Office of Economy, Infrastructure and Urban Affairs','Ward'),
    'Trường học / Giáo dục':('Office of Culture and Society','Ward'),
    'UBND: Khoa học & Công nghệ':('Office of Culture and Society','Ward'),
    'Báo chí':('Office of Culture and Society','Ward'),
    'Quản lý thị trường':('Vertically organised/provincial recipient','Province'),
}
fun=clean['Q1.7'].fillna('').astype(str).str.strip().value_counts().rename_axis('Recorded domain').reset_index(name='n in sample')
fun[['Post-reform recipient','Tier']]=fun['Recorded domain'].apply(lambda x: pd.Series(domain_map.get(x,('Unresolved recipient','Unresolved'))))
fun.to_csv(OUT/'function_crosswalk.csv',index=False)
groups=fun.groupby(['Post-reform recipient','Tier'],as_index=False)['n in sample'].sum().sort_values('n in sample')
assert int(groups['n in sample'].sum()) == len(clean)
fig,ax=plt.subplots(figsize=(8.8,4.6));colors=[grey if t=='Province' else teal for t in groups.Tier]
ax.barh(groups['Post-reform recipient'],groups['n in sample'],color=colors)
for i,v in enumerate(groups['n in sample']):ax.text(v+.1,i,str(v),va='center')
ax.set_xlabel('Respondents whose recorded functional domain maps to recipient')
ax.set_title('Legal destination of recorded functional domains')
ax.text(.01,-.22,'Descriptive crosswalk only: recorded domain does not establish the respondent’s administrative tier.',transform=ax.transAxes,fontsize=9)
ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'Figure3_function_crosswalk.png',dpi=300,bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(9,4.5));
for col,label,color in [('education','Education facilities',teal),('food_outlet','Food outlets',orange),('religious_premises','Religious premises',grey),('shop','Shops',navy)]:
    base=float(snap.iloc[0][col]);ax.plot(range(len(snap)),100*snap[col]/base,marker='o',label=label,color=color)
ax.axhline(100,color='black',lw=1);ax.set_xticks(range(len(snap)),snap.date,rotation=30,ha='right');ax.set_ylabel('Index, 1 Jan 2026 = 100');ax.set_title('Mapped stock sensitivity within 2026');ax.legend(frameon=False,ncol=2);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'Figure4_osm_sensitivity.png',dpi=300);plt.close(fig)

result={'verified_n':len(clean),'timestamp_min':str(clean.Timestamp.min()),'timestamp_max':str(clean.Timestamp.max()),'raw_item_checks':checks,'years_in_post':{'mean':float(clean.SoNamCT.mean()),'median':float(clean.SoNamCT.median()),'min':int(clean.SoNamCT.min()),'max':int(clean.SoNamCT.max())},'rescaling':rescale,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.clean_authorities,args.raw_authorities]},'excluded_post_reform_interview_data':True,'interpretation':'Respondents are local public-sector practitioners; the available fields do not establish that all belonged to the abolished tier.'}

# --- Spatial context maps ---------------------------------------------------
ROOT=P.parents[1]
ward_geo_path=args.ward_geojson or ROOT/'OpenData/ThuDucCity_ward.geojson'
vietnam_geo_path=args.vietnam_geojson or ROOT/'OpenData/gis_vietnam/geoboundaries_VNM_ADM0.geojson'
poi_path=args.poi_gpkg or ROOT/'Paper4/DataPaper4/01_osm_vectors/2026/osm_2026_pois.gpkg'
ward_geo=json.loads(ward_geo_path.read_text(encoding='utf-8'))
vn_geo=json.loads(vietnam_geo_path.read_text(encoding='utf-8'))
MERGE={
 'Hiep Binh':['Hiệp Bình Chánh','Hiệp Bình Phước','Linh Đông*'],
 'Thu Duc':['Bình Thọ','Linh Chiểu','Trường Thọ','Linh Tây*','Linh Đông*'],
 'Tam Binh':['Bình Chiểu','Tam Phú','Tam Bình'],
 'Linh Xuan':['Linh Trung','Linh Xuân','Linh Tây*'],
 'Tang Nhon Phu':['Tân Phú','Hiệp Phú','Tăng Nhơn Phú A','Tăng Nhơn Phú B','Long Thạnh Mỹ*'],
 'Long Binh':['Long Bình','Long Thạnh Mỹ*'],'Long Phuoc':['Trường Thạnh','Long Phước'],
 'Long Truong':['Phú Hữu','Long Trường'],'Cat Lai':['Thạnh Mỹ Lợi','Cát Lái'],
 'Binh Trung':['Bình Trưng Đông','Bình Trưng Tây','An Phú*'],
 'Phuoc Long':['Phước Bình','Phước Long A','Phước Long B'],
 'An Khanh':['Thủ Thiêm','An Lợi Đông','Thảo Điền','An Khánh','An Phú*']}
def norm(s):
    s=unicodedata.normalize('NFD',str(s).lower().replace('phường','')).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
assign={};split=set()
for new,old in MERGE.items():
    for w in old:
        k=norm(w.rstrip('*'));assign.setdefault(k,[]).append(new)
        if w.endswith('*'):split.add(k)
palette=dict(zip(MERGE,plt.cm.tab20(np.linspace(0,1,len(MERGE)))))
def rings(geom):
    cs=geom['coordinates']
    if geom['type']=='Polygon':return [cs[0]]
    return [p[0] for p in cs]
def centroid_of(feature):
    pts=[p for ring in rings(feature['geometry']) for p in ring]
    return np.mean([p[0] for p in pts]),np.mean([p[1] for p in pts])

fig,ax=plt.subplots(figsize=(9.4,7.2))
for ft in ward_geo['features']:
    key=norm(ft['properties']['Ten']); owners=assign.get(key,['Unassigned'])
    color=palette.get(owners[0],(0.85,0.85,0.85,1))
    for ring in rings(ft['geometry']):
        ax.add_patch(Polygon(ring,facecolor=color,edgecolor='white',lw=.8,alpha=.72,hatch='///' if key in split else None))
for new,olds in MERGE.items():
    feats=[f for f in ward_geo['features'] if new in assign.get(norm(f['properties']['Ten']),[])]
    if feats:
        x,y=np.mean([centroid_of(f) for f in feats],axis=0);ax.text(x,y,new,ha='center',va='center',fontsize=7,fontweight='bold')
allpts=np.array([p for f in ward_geo['features'] for ring in rings(f['geometry']) for p in ring])
ax.set_xlim(allpts[:,0].min()-.015,allpts[:,0].max()+.015);ax.set_ylim(allpts[:,1].min()-.01,allpts[:,1].max()+.01);ax.set_aspect(1/np.cos(np.deg2rad(allpts[:,1].mean())))
ax.set_title('Former Thu Duc City: legal allocation of 34 wards to 12 successors',fontweight='bold')
ax.text(.01,.01,'Colours show successor allocation under Resolution 1685. Hatched former wards are split;\nexact digital successor boundaries were unavailable and are not inferred.',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
ax.axis('off')
inset=ax.inset_axes([.01,.68,.18,.28])
for ft in vn_geo['features']:
    for ring in rings(ft['geometry']):inset.add_patch(Polygon(ring,facecolor='#e8edf2',edgecolor='#5d6b78',lw=.5))
inset.scatter([106.7],[10.8],s=24,c='#d55e00',zorder=3);inset.text(106.7,10.8,'  HCMC',fontsize=7,va='center');inset.autoscale();inset.axis('off')
fig.tight_layout();fig.savefig(OUT/'Figure1_study_area.png',dpi=300,bbox_inches='tight');plt.close(fig)

# Read point features directly from the GeoPackage (all geometries are EPSG:4326 points).
con=sqlite3.connect(poi_path);pois=[]
for blob,amenity,shop in con.execute('select geom,amenity,shop from osm_2026_pois'):
    if blob and len(blob)>=29 and blob[8]==1 and struct.unpack('<I',blob[9:13])[0]==1:
        x,y=struct.unpack('<dd',blob[13:29]);
        cat=('Education' if amenity in {'school','college','university','kindergarten'} else 'Health' if amenity in {'hospital','clinic','doctors','pharmacy','dentist'} else 'Public service' if amenity in {'townhall','community_centre','police','fire_station','post_office','library'} else None)
        if cat:pois.append((x,y,cat))
con.close()
pop_by={norm(r.Ward):(float(r.Pop_2025),float(r.area_km2)) for _,r in before.iterrows()}
dens=[]
for f in ward_geo['features']:
    key=norm(f['properties']['Ten']);dens.append(pop_by.get(key,(np.nan,np.nan))[0]/pop_by.get(key,(np.nan,np.nan))[1])
vmin,vmax=np.nanpercentile(dens,[5,95]);cmap=plt.cm.YlOrRd
fig,ax=plt.subplots(figsize=(9.4,7.2))
for ft,density in zip(ward_geo['features'],dens):
    color=cmap(np.clip((density-vmin)/(vmax-vmin),0,1)) if np.isfinite(density) else '#dddddd'
    for ring in rings(ft['geometry']):ax.add_patch(Polygon(ring,facecolor=color,edgecolor='white',lw=.6))
markers={'Education':('o','#2468a2'),'Health':('^','#278c6d'),'Public service':('s','#6b4c9a')}
for cat,(marker,color) in markers.items():
    pts=np.array([(x,y) for x,y,c in pois if c==cat and allpts[:,0].min()<=x<=allpts[:,0].max() and allpts[:,1].min()<=y<=allpts[:,1].max()])
    if len(pts):ax.scatter(pts[:,0],pts[:,1],s=9,marker=marker,c=color,label=f'{cat} OSM POIs',alpha=.78,edgecolors='none')
ax.set_xlim(allpts[:,0].min(),allpts[:,0].max());ax.set_ylim(allpts[:,1].min(),allpts[:,1].max());ax.set_aspect(1/np.cos(np.deg2rad(allpts[:,1].mean())));ax.axis('off')
ax.set_title('Population-density surface and selected mapped service points',fontweight='bold')
sm=plt.cm.ScalarMappable(cmap=cmap,norm=plt.Normalize(vmin=vmin,vmax=vmax));cb=fig.colorbar(sm,ax=ax,fraction=.035,pad=.02);cb.set_label('Modelled residents per km² (former-ward allocation)')
ax.legend(frameon=True,loc='upper right',fontsize=8);ax.text(.01,.01,'GHS-POP allocation is modelled; OSM points indicate mapped features, not verified operating facilities.',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
fig.tight_layout();fig.savefig(OUT/'Figure2_spatial_exposure.png',dpi=300,bbox_inches='tight');plt.close(fig)

# Institutional restructuring flowchart.
fig,ax=plt.subplots(figsize=(11,5.5));ax.set_xlim(0,11);ax.set_ylim(0,6);ax.axis('off')
def box(x,y,w,h,text,color):
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04,rounding_size=.08',fc=color,ec='#334455',lw=1.2);ax.add_patch(p);ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9,fontweight='bold',wrap=True);return p
box(.2,4.5,3.0,.8,'Ho Chi Minh City\n(provincial level)','#dce6f1');box(.2,2.8,3.0,.9,'Thu Duc City\nintermediate tier removed','#f4cccc');box(.2,.8,3.0,1.1,'34 former wards\nlocal delivery and local knowledge','#d9ead3')
box(7.6,4.5,3.0,.8,'Ho Chi Minh City\n(provincial level)','#dce6f1');box(7.6,.4,3.0,.8,'12 successor wards\nenlarged territorial exposure','#d9ead3')
offices=[("People's Council &\nPeople's Committee",3.1),('Economy, Infrastructure\n& Urban Affairs',2.0),('Culture & Society',.9)]
for txt,y in offices:box(4.25,y,2.6,.72,txt,'#fff2cc')
for a,b in [((1.7,4.5),(1.7,3.7)),((1.7,2.8),(1.7,1.9)),((3.2,3.25),(4.25,3.45)),((3.2,3.25),(4.25,2.35)),((3.2,3.25),(4.25,1.25)),((6.85,3.45),(7.6,4.75)),((6.85,2.35),(7.6,4.75)),((6.85,1.25),(7.6,.8))]:ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,lw=1.2,color='#52616b'))
ax.text(5.5,5.55,'2025 shift from three tiers to two tiers and three specialised ward offices',ha='center',fontsize=12,fontweight='bold');ax.text(5.5,.05,'Legal destination does not demonstrate staffing, records transfer, operational capacity or service outcomes.',ha='center',fontsize=9)
fig.tight_layout();fig.savefig(OUT/'Figure3_institutional_restructuring.png',dpi=300,bbox_inches='tight');plt.close(fig)

# Three-part audit framework.
fig,ax=plt.subplots(figsize=(10.5,4.4));ax.set_xlim(0,10.5);ax.set_ylim(0,4.4);ax.axis('off')
steps=[(0.3,'1  LEGAL RECIPIENT','Who has formal authority?','law • function • coordination'),(3.75,'2  TERRITORIAL EXPOSURE','What is assigned to the unit?','people • area • assets • mapped objects'),(7.2,'3  TRANSFER OUTCOME','Can the successor retrieve and act?','records • routines • contacts • response time')]
for x,title,question,items in steps:
    ax.add_patch(FancyBboxPatch((x,.9),3.0,2.4,boxstyle='round,pad=.08',fc='#edf3f8',ec='#244363',lw=1.5));ax.text(x+1.5,2.8,title,ha='center',fontweight='bold',color='#244363');ax.text(x+1.5,2.15,question,ha='center',fontsize=10);ax.text(x+1.5,1.45,items,ha='center',fontsize=8.5,color='#48545e')
for x in [3.35,6.8]:ax.add_patch(FancyArrowPatch((x,2.1),(x+.35,2.1),arrowstyle='-|>',mutation_scale=16,lw=1.5,color='#d4741c'))
ax.text(5.25,4.0,'An auditable framework for evaluating administrative rescaling',ha='center',fontsize=13,fontweight='bold');ax.text(5.25,.35,'The present study observes Steps 1–2. Step 3 requires genuine post-reform workflow and field evidence.',ha='center',fontsize=9,fontstyle='italic')
fig.tight_layout();fig.savefig(OUT/'Figure7_audit_framework.png',dpi=300,bbox_inches='tight');plt.close(fig)

# Internal OSM fitness-for-purpose diagnostics (not external ground truth).
ward_osm=pd.read_csv(args.legacy_tables/'osm_ward_year_counts.csv')
last=ward_osm[ward_osm['date']==ward_osm['date'].max()].pivot_table(index='ward',columns='metric',values='value',aggfunc='sum').fillna(0)
pop=pd.Series({r.Ward:r.Pop_2025 for _,r in before.iterrows()},name='population')
diag=[]
for metric in ['education','health','public_space','food_outlet','shop','road_km']:
    if metric not in last:continue
    joined=pd.concat([last[metric],pop],axis=1,join='inner').dropna()
    diag.append({'metric':metric,'wards_n':len(joined),'zero_share_%':100*(joined[metric]==0).mean(),'spearman_population':joined[metric].corr(joined.population,method='spearman')})
pd.DataFrame(diag).to_csv(OUT/'osm_fitness_diagnostics.csv',index=False)
result['osm_fitness_diagnostics']=diag
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True,indent=2))
