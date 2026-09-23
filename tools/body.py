# python3 tools/body.py  (numpy, scipy, pillow)
# Pre-compose le corps d un seul bloc : veste + bassin (jean) dans la pose de repos du rig,
# couleurs des pieces d origine, contour d encre retire puis UN contour unique redessine autour de la silhouette
# entiere (teinte de l encre de la piece la plus proche). Seules lignes internes conservees : les bords de la
# veste qui passent sur une autre piece (ourlet et dos sur le jean), qui sont des bords de vetement.
# Sorties : body.png (corps entier), body_top.png (la veste seule, redessinee par-dessus la jambe avant),
#           head_b.png (tete dont le cou est prolonge jusque dans le col : le col le recouvre), metadonnees JSON.
import numpy as np, json, os
from PIL import Image
from scipy import ndimage as ndi
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','cutout')+'/'
SPINE,NECK,HEAD=0.5,0.07,0.132
MPP=0.00104                      # m/px du corps (celui du bassin)
OUT_M=0.0050                     # epaisseur du contour (m) : ~1 px css a 900 px de haut, comme le trait des membres
def load(n): return np.asarray(Image.open(D+n+'.png')).astype(np.float32)
def defill(im,t_in=5.0,erode=1.2):
    a=im[...,3]>128; d=ndi.distance_transform_edt(a); inner=d>t_in
    _,(iy,ix)=ndi.distance_transform_edt(~inner,return_indices=True)
    out=im.copy(); ring=~inner; out[ring,:3]=im[iy[ring],ix[ring],:3]
    sa=ndi.gaussian_filter((d>erode).astype(np.float32),0.6); out[...,3]=np.minimum(im[...,3],255*sa)
    return out
def ink(im,t_in=4.0):
    a=im[...,3]>200; d=ndi.distance_transform_edt(a); px=im[a&(d<t_in)][:,:3]
    px=px[px.mean(1)<np.percentile(px.mean(1),30)]; return np.median(px,0)
def ring(im,t_in=6.0):
    a=im[...,3]>100; d=ndi.distance_transform_edt(a); return (a&(d<=t_in)).astype(np.float32)*255
torso,pelvis,neck,head=load('torso'),load('pelvis_t'),load('neck'),load('head')
INK={'torso':ink(torso),'pelvis':ink(pelvis)}
# --- placement de chaque piece dans le repere monde du corps (x avant, y haut, origine = hanche) ---
# une piece = (image, point image u0, point monde w0, vecteur monde de l axe image x, de l axe image y (vers le bas))
def frame_from(up_img,s,sx=None):
    # up_img : vecteur image (y bas) qui doit pointer vers le haut monde ; s : m/px
    ux,uy=up_img[0],-up_img[1]; phi=np.pi/2-np.arctan2(uy,ux); c,sn=np.cos(phi),np.sin(phi)
    R=lambda v:np.array([c*v[0]-sn*v[1],sn*v[0]+c*v[1]])
    ex=R((1,0))*(sx or s); ey=R((0,-1))*s; return ex,ey
T_top,T_bot=np.array([95,40.]),np.array([75,395.])
ex,ey=frame_from(T_top-T_bot,0.00152)
PT=dict(torso=(torso,T_top,np.array([0,SPINE]),ex,ey))
PT['pelvis']=(pelvis,np.array([150,138.]),np.array([0,0.]),np.array([MPP,0]),np.array([0,-MPP]))
ORDER=['pelvis','torso']
# boite englobante
pts=[]
for n,(im,u0,w0,ax,ay) in PT.items():
    h,w=im.shape[:2]
    for cx,cy in [(0,0),(w,0),(0,h),(w,h)]: pts.append(w0+ax*(cx-u0[0])+ay*(cy-u0[1]))
pts=np.array(pts); PAD=12
xmin,ymin=pts.min(0); xmax,ymax=pts.max(0)
Wd=int(np.ceil((xmax-xmin)/MPP))+2*PAD; Hd=int(np.ceil((ymax-ymin)/MPP))+2*PAD
X,Y=np.meshgrid(np.arange(Wd)+0.5,np.arange(Hd)+0.5)
WX=xmin+(X-PAD)*MPP; WY=ymax-(Y-PAD)*MPP
def place(im,u0,w0,ax,ay):
    M=np.array([[ax[0],ay[0]],[ax[1],ay[1]]]); Mi=np.linalg.inv(M)
    dx,dy=WX-w0[0],WY-w0[1]; u=u0[0]+Mi[0,0]*dx+Mi[0,1]*dy; vv=u0[1]+Mi[1,0]*dx+Mi[1,1]*dy
    pm=np.concatenate([im[...,:3]*im[...,3:]/255,im[...,3:]],-1)
    return np.stack([ndi.map_coordinates(pm[...,c],[vv-0.5,u-0.5],order=1,mode='constant',cval=0) for c in range(4)],-1)
def over(dst,src): a=src[...,3:]/255; return src+dst*(1-a)
TIN={'pelvis':8.0,'torso':5.0}
L={n:place(defill(PT[n][0],TIN[n]),*PT[n][1:]) for n in ORDER}
# bassin : la ceinture ne depasse plus derriere la veste. Au-dessus du centre du cercle d assise, le jean est
# rogne au cercle ajuste sur le bas de son contour (raccord tangent au dos de la veste)
pa=L['pelvis'][...,3]>128; e=pa&~ndi.binary_erosion(pa); m=e&(WY<-0.03)
xs,ys=WX[m],WY[m]; Am=np.c_[2*xs,2*ys,np.ones_like(xs)]; cx,cy,c0=np.linalg.lstsq(Am,xs**2+ys**2,rcond=None)[0]
rr=np.sqrt(c0+cx*cx+cy*cy); dd=np.hypot(WX-cx,WY-cy)
keep=np.where(WY>cy,np.clip((rr-dd)/MPP+0.5,0,1),1.0); L['pelvis']*=keep[...,None]
comp=np.zeros((Hd,Wd,4),np.float32); owner=np.full((Hd,Wd),-1)
for i,n in enumerate(ORDER):
    comp=over(comp,L[n]); owner[L[n][...,3]>20]=i
# lignes internes : bords de la veste (trait d origine) poses sur une autre piece
T_orig=place(*PT['torso']); T_ring=place(np.dstack([np.zeros(torso.shape[:2]+(3,)),ring(torso)]),*PT['torso'][1:])[...,3]/255
other=L['pelvis'][...,3]>128
M=T_ring*ndi.binary_dilation(other,iterations=3)*(T_orig[...,3]/255)
comp=comp*(1-M[...,None])+T_orig*M[...,None]
# contour unique autour de l union
A=comp[...,3]/255
_,(jy,jx)=ndi.distance_transform_edt(~(A>0.5),return_indices=True)
rgb=np.where((A>0.5)[...,None],comp[...,:3]/np.maximum(A,1e-3)[...,None],(comp[...,:3]/np.maximum(A,1e-3)[...,None])[jy,jx])
Sm=ndi.gaussian_filter(A,1.4); inside=Sm>0.5; As=np.clip((Sm-0.5)*3.6+0.5,0,1)   # bord lisse, anti-crenele ~1 px
d,(iy,ix)=ndi.distance_transform_edt(~inside,return_indices=True)
w=OUT_M/MPP; oa=np.clip(w+0.5-d,0,1)
own=owner[iy,ix]; inkc=np.zeros((Hd,Wd,3),np.float32)+INK['torso']
for i,n in enumerate(ORDER): inkc[own==i]=INK[n]
fin=rgb*As[...,None]+inkc*(1-As[...,None]); al=np.maximum(As,oa)
body=np.concatenate([fin*al[...,None],al[...,None]*255],-1)
def unpm(c):
    a=c[...,3:]; rgb=np.where(a>0.5,c[...,:3]*255/np.maximum(a,1e-3),0); return np.concatenate([rgb,a],-1).clip(0,255).astype(np.uint8)
Image.fromarray(unpm(body)).save(D+'body.png')
# veste seule (+ son contour) : pixels dont la piece la plus proche / du dessus est la veste
ti=ORDER.index('torso'); tm=ndi.gaussian_filter(((own==ti)&~inside | (owner==ti)).astype(np.float32),0.7)
# la veste recouvre toute sa propre surface (ourlet compris), pas le jean ni le cou dessous
tm=np.maximum(np.minimum(tm,1),0)
top=np.concatenate([body[...,:3]*tm[...,None],body[...,3:]*tm[...,None]],-1)
Image.fromarray(unpm(top)).save(D+'body_top.png')
# tete : le moignon de cou (bas coupe en biais de (152,295) a (246,337)) est prolonge jusqu a Y_EXT par la piece
# cou (texture recalee sur la peau du moignon, contour retire), glissee DESSOUS la tete depuis la nuque (y=235) :
# bord arriere net sous le bord detoure de la tete, bord avant dans le prolongement de la gorge, bas effile pour
# rester dans le col quand la tete bouge. La coupe en biais est fondue. L axe de la tete est au bord haut du col
# (4 cm au-dessus du point cou du rig) : le cou entre dans le col de la veste, redessine par-dessus.
C_HEAD=np.array([228,160.]); HMPP=0.00109; HEADPIV=0.04          # axe de la tete : haut du col (index.html)
Y_EXT=int(C_HEAD[1]+(NECK+HEAD+0.05)/HMPP); PIV_Y=C_HEAD[1]+(NECK+HEAD-HEADPIV)/HMPP; H0,W0=head.shape[:2]; YT=235
nk=defill(neck,5.0); ny0,ny1=40,120
xs_n=np.nonzero(nk[80,:,3]>128)[0]; nx0,nx1=xs_n.min()+1,xs_n.max()-1
Yh,Xh=np.mgrid[0:Y_EXT+4,0:W0].astype(np.float32)
sm=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
XB=151+34*sm((Yh-(PIV_Y-15))/(Y_EXT-PIV_Y+15))                 # nuque droite puis effilement dans le col
XF=253-7*np.clip((Yh-286)/51,0,None)-10*sm((Yh-PIV_Y)/(Y_EXT-PIV_Y))  # gorge prolongee
u=nx0+(Xh-XB)/np.maximum(XF-XB,1)*(nx1-nx0); v=ny0+((Yh-YT)%(2*(Y_EXT-YT)))/(Y_EXT-YT)*(ny1-ny0)
col=np.stack([ndi.map_coordinates(nk[...,c],[v,u],order=1,mode='nearest') for c in range(3)],-1)
ca=np.clip(Xh-XB+0.5,0,1)*np.clip(XF-Xh+0.5,0,1)*np.clip(Yh-YT,0,1)*np.clip(Y_EXT-Yh,0,1)
hd=np.zeros((Y_EXT+4,W0,4),np.float32); hd[:H0]=head
ah=head[...,3]>128; dcut=ndi.distance_transform_edt(ah)
fade=np.ones((H0,W0),np.float32); zone=(np.arange(H0)[:,None]>292)&(np.arange(W0)[None,:]<262)
fade[zone]=np.clip((dcut[zone]-2.5)/9,0,1); fade=fade*fade*(3-2*fade)
# nuque : frange de detourage de la tete rognee (1.5 px), le cou net passe dessous
nape=(np.arange(H0)[:,None]>225)&(np.arange(W0)[None,:]<205)
fade[nape]=np.minimum(fade[nape],np.clip((dcut[nape]-1.5)/1.5,0,1))
hd[:H0,:,3]*=fade
ref=head[(dcut>10)&zone&(head[...,0]>140)][:,:3]; cm=col[(ca>0.99)&(Yh>300)]
col=np.clip((col-np.median(cm,0))*(ref.std(0)/np.maximum(cm.std(0),1e-3))+np.median(ref,0),0,255)
ha=hd[...,3:]/255; rgb=hd[...,:3]*ha+col*(1-ha)*ca[...,None]; al=ha[...,0]+(1-ha[...,0])*ca
hb2=np.concatenate([rgb/np.maximum(al,1e-3)[...,None],al[...,None]*255],-1)
Image.fromarray(hb2.clip(0,255).astype(np.uint8)).save(D+'head_b.png')
hip=[PAD-xmin/MPP,PAD+ymax/MPP]
def px(wx,wy): return [round(PAD+(wx-xmin)/MPP,1),round(PAD+(ymax-wy)/MPP,1)]
# CUT.body dans index.html : hip = pivot des jambes ; wy = ligne de la legere rotation du bassin (3 cm au-dessus de la hanche)
print(json.dumps(dict(mpp=MPP,w=Wd,h=Hd,hip=px(0,0),wy=px(0,0.03)[1],neck=px(0,SPINE),ink={k:[int(c) for c in v] for k,v in INK.items()})))
