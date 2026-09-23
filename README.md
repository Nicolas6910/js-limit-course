# js-limit-course

Cycle de marche puis course d'un personnage 2D en canvas 2D, rig entierement procedural, habille facon cut-out (papier decoupe) avec de vraies images.

- Rig articule : IK deux os pour les jambes, pieds ancres au sol en appui (zero glissement), deroule talon/pointe
- Allure pilotee par la vitesse : cadence, longueur de pas, facteur d'appui (62 % marche -> 31 % course, phase de vol)
- Poids : bassin en pendule inverse a la marche, ressort-masse a la course, contrainte de portee de jambe
- Anticipation (accroupi + recul avant le depart et avant la course), freinage avec pied pose en avant et buste en arriere, recuperation essoufflee
- Ressorts secondaires : buste, tete, bras, queue de cheval en Verlet
- Rue de nuit avec 7 plans de parallaxe et sol en perspective

## Habillage cut-out

Une image PNG detouree par segment, dans `assets/cutout/` : tete, cou, torse (veste), bassin, cuisse, tibia (jean),
chaussure (coupee en deux au pli metatarsien pour le deroule), bras, avant-bras, main, queue de cheval, et pour le visage
oeil ouvert, paupiere fermee, bouche fermee / entrouverte / grande ouverte (clignement et halètement pendant la recuperation).
Un seul bloc : cou, buste et bassin ne sont plus des pieces separees mais une image de corps pre-composee
(`body.png`, `tools/body.py` : veste + jean poses dans la pose de repos du rig, contour d encre retire puis un contour
unique redessine autour de la silhouette entiere ; seuls restent les bords de vetement, ourlet de la veste sur le jean).
Le rig laisse le buste glisser (+-4,6 cm) et tourner (-9,5 a +6 deg) sur le bassin : le rendu habille le fige, le
corps est rigide sur l axe hanche -> cou et seule une legere rotation du bassin est gardee, bornee en douceur a +-4 deg
(tranches interpolees a la taille, autour du pivot de hanche). Tout le reste pivote sur des axes fixes du corps : les deux
jambes sur un pivot de hanche unique (re-resolues par IK depuis ce pivot, les pieds d appui gardent exactement leur
position), les bras sur des epaules fixes, la tete sur le bord haut du col. Le cou appartient a la tete (`head_b.png` :
moignon prolonge par la piece cou, recale en teinte) et entre dans le col ; la veste seule (`body_top.png`) est
redessinee par-dessus la racine de la cuisse avant et la base du cou, si bien qu aucun pivot n est visible.

Membres : cuisse+tibia et bras+avant-bras sont une seule bande continue par membre (`leg.png`, `arm.png`, `tools/joints.py`),
pliee au genou/coude par skinning 2D (tranches fines tournant d un angle interpole autour du pivot), avec un conge
texture dans le creux du pli (plus de V a l arriere du genou ni au pli du coude) et un ourlet de jean plat en biais.
Chaque membre est compose hors ecran puis entoure d un seul contour (dilatation de la silhouette) ; le contour de la
jambe avant s efface dans tout le jean du corps (cuisse et bassin ne font qu un), celui du bras avant pres de l epaule.
Ordre : bras et jambe du fond (assombris, racine opaque), corps, jambe avant, tete, veste, queue de cheval, bras avant.
Degrades plein ecran du decor (ciel, halo de lune, vignette) rasterises une fois par taille d ecran.

Images generees avec Agnes (`agnes-image-2.5-flash`), une piece par prompt avec un prefixe de style commun
(« paper craft cut-out puppet part … solid chroma green background ») et des couleurs fixees
(veste orange brule a liseré blanc, jean bleu marine, baskets blanches a semelle corail). Detourage par chroma key
numpy/scipy (distance au vert, erosion de frange, despill), alignement de l'axe principal par ACP, teinte du cou et de la
queue de cheval recalee sur la tete.

Touche S ou bouton « Squelette » : version non habillee (rendu procedural d'origine) + rig. Boucle de 16 s, bouton Rejouer.
`?t=11.2` fige le temps (captures), `?sk=1` force le squelette.

![course](course.png)
![recuperation](recuperation.png)

Rendu procedural d origine, avant habillage (toujours visible via le mode Squelette) :

![marche](walk.png)
![course procedurale](run.png)
