# python3 tools/joints.py  (numpy, scipy, pillow)
# Construit les bandes continues bras (uarm+farm) et jambe (thigh+shin) pour le rendu sans jointure.
# - contour sombre retire (couleur de l interieur propagee dans le liseré), le contour est redessine en JS autour de l union
# - teinte du segment distal recalee sur le segment proximal (et bassin recale sur la cuisse)
# - largeur raccordee au pivot central (effilement lineaire), fondu enchaine sur une bande autour du pivot
# - calotte proximale adoucie (alpha) : elle disparait sous le bassin / l epaule
# - jambe : ourlet plat en biais, bas legerement evase (au lieu d un bout de tube arrondi)
import numpy as np, json, sys
from PIL import Image
from scipy import ndimage as ndi
import os
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','cutout')+'/'; O=D   # sources : pieces d origine, jamais ecrasees
L1,L2,UA,FA=0.46,0.445,0.29,0.27
def load(n): return np.asarray(Image.open(O+n+'.png')).astype(np.float32)
def defill(im,t_in=5.0,erode=1.4):
    a=im[...,3]>128; d=ndi.distance_transform_edt(a)
    inner=d>t_in
    _,(iy,ix)=ndi.distance_transform_edt(~inner,return_indices=True)
    out=im.copy(); ring=~inner
    out[ring,:3]=im[iy[ring],ix[ring],:3]   # couleur interieure propagee dans le liseré ET au dela (pas de frange noire au reechantillonnage)
    # alpha : bord net anti-crenele, legerement erode (retire la frange d encre)
    sa=ndi.gaussian_filter((d>erode).astype(np.float32),0.6)
    out[...,3]=np.minimum(im[...,3],255*sa)
    return out
def stats(im,excl_bright=False):
    a=im[...,3]>200; d=ndi.distance_transform_edt(a); m=a&(d>6)
    px=im[m][:,:3]
    if excl_bright: px=px[px.mean(1)<150]
    return np.median(px,0),np.percentile(px,75,0)-np.percentile(px,25,0)+1e-3
def retint(im,ref,excl_bright=False):
    m0,s0=stats(im,excl_bright); m1,s1=stats(ref,excl_bright)
    out=im.copy(); out[...,:3]=np.clip((im[...,:3]-m0)*(s1/s0)+m1,0,255); return out
def rows_w(a,y):
    xs=np.nonzero(a[int(round(y))]>128)[0]; return (xs.min()+xs.max())/2,(xs.max()-xs.min()+1)
def mid(im,p0,p1):
    # ligne mediane lissee (quadratique) de la silhouette entre les pivots : la bande sort droite
    key=id(im)
    if key in _mc: return _mc[key]
    a=im[...,3]; ys=np.arange(int(p0[1]),int(p1[1])+1)
    c=np.array([rows_w(a,y)[0] for y in ys]); f=np.polyfit(ys,c,2)
    yy=np.arange(im.shape[0]); m=np.polyval(f,np.clip(yy,p0[1],p1[1]))
    _mc[key]=m; return m
_mc={}
def strip(up,lo,pu,pl,Lu,Ll,s,band=6,fade=1.0,pad=4,fext=0.0):
    # up/lo: images RGBA (axe vertical), pu/pl: (p0,p1) pivots, s: px/m de sortie
    su=(pu[1][1]-pu[0][1])/Lu; sl=(pl[1][1]-pl[0][1])/Ll
    au,al=up[...,3],lo[...,3]
    _,wuJ=rows_w(au,pu[1][1]); _,wlJ=rows_w(al,pl[0][1])
    wJ=0.5*(wuJ*s/su+wlJ*s/sl)                        # largeur cible au pivot central
    kuJ=wJ/(wuJ*s/su); klJ=wJ/(wlJ*s/sl)
    rtop=pu[0][1]*s/su; rbot=(lo.shape[0]-pl[1][1])*s/sl
    YA=rtop+pad; YJ=YA+Lu*s; YB=YJ+Ll*s; Hh=int(np.ceil(YB+rbot+pad))
    Wd=int(np.ceil(max(up.shape[1]*s/su,lo.shape[1]*s/sl*klJ)))+2*pad; CX=Wd/2
    Y,X=np.mgrid[0:Hh,0:Wd].astype(np.float32)
    def sample(im,p0,p1,sp,Y0,kJ,upper):
        # ligne source correspondant a Y ; centre d axe interpole entre p0 et p1
        ys=p0[1]+(Y-Y0)*sp/s
        t=np.clip((ys-p0[1])/(p1[1]-p0[1]),0,1)
        cx=np.interp(ys,np.arange(len(mid(im,p0,p1))),mid(im,p0,p1))
        kk=1+(kJ-1)*(t if upper else 1-t)                 # effilement : 1 au bout, kJ au pivot central
        xs=cx+(X-CX)*sp/s/kk
        ch=[ndi.map_coordinates(im[...,c],[ys,xs],order=1,mode='constant',cval=0) for c in range(4)]
        return np.stack(ch,-1)
    U=sample(up,pu[0],pu[1],su,YA,kuJ,True); Lw=sample(lo,pl[0],pl[1],sl,YJ,klJ,False)
    w=np.clip((Y-(YJ-band))/(2*band),0,1)[...,None]; w=w*w*(3-2*w)
    # premultiplie pour le fondu
    def pm(c): return np.concatenate([c[...,:3]*c[...,3:]/255,c[...,3:]],-1)
    R=pm(U)*(1-w)+pm(Lw)*w
    a=R[...,3:]; rgb=np.where(a>0.5,R[...,:3]*255/np.maximum(a,1e-3),0)
    out=np.concatenate([rgb,a],-1)
    # calotte proximale : alpha adouci de son sommet jusqu au pivot
    f=np.clip((Y-(YA-rtop))/(rtop*(fade+fext)),0,1); f=f*f*(3-2*f)
    out[...,3]*=f
    return out.clip(0,255).astype(np.uint8),dict(s=s,cx=CX,A=YA,J=YJ,B=YB,rJ=wJ/2,rA=rows_w(au,pu[0][1])[1]*s/su/2,w=Wd,h=Hh)
th,sh,ua,fa,pv=load('thigh'),load('shin'),load('uarm'),load('farm'),load('pelvis')
to=load('torso')
sh=retint(sh,th); pv2=retint(pv,th); fa=retint(fa,to,True); ua=retint(ua,to,True)
th,sh,ua,fa=defill(th,6.5),defill(sh,6),defill(ua,6),defill(fa,6)
leg,ML=strip(th,sh,((43,43),(43,268)),((34.5,35.5),(34,275)),L1,L2,500)
arm,MA=strip(ua,fa,((46,43),(45,267)),((44,44),(41.5,274.5)),UA,FA,760,band=12,fext=0.35)
def hem(im,M,drop=5.0,slope=0.18,flare=1.1,band=40):
    # ourlet du jean : le bas n est plus un tube arrondi mais une coupe droite, un peu en biais (plus longue au
    # talon, cote -x de la bande) et legerement evasee sur les `band` px au-dessus
    im=im.astype(np.float32); H,W=im.shape[:2]; cx,B=M['cx'],M['B']
    Y,X=np.mgrid[0:H,0:W].astype(np.float32)
    f=1+(flare-1)*np.clip((Y-(B-band))/band,0,1)**2
    xs=cx+(X-cx)/f; out=np.stack([ndi.map_coordinates(im[...,c],[Y,xs],order=1,mode='constant') for c in range(4)],-1)
    yh=B+drop-slope*(X-cx); out[...,3]*=np.clip(yh-Y+0.5,0,1)
    return out.clip(0,255).astype(np.uint8)
leg=hem(leg,ML)
Image.fromarray(leg).save(D+'leg.png'); Image.fromarray(arm).save(D+'arm.png')
Image.fromarray(pv2.clip(0,255).astype(np.uint8)).save(D+'pelvis_t.png')
print(json.dumps({'leg':ML,'arm':MA},default=lambda v:round(float(v),1)))
