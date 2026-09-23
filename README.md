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
Chaque piece est rigide : elle pivote sur son articulation (constantes `CUT` dans `index.html` : pivots proximal/distal en pixels,
longueur cible en metres), ses extremites sont arrondies en capsule pour recouvrir l'articulation, et les membres arriere
sont assombris et dessines derriere le corps.

Images generees avec Agnes (`agnes-image-2.5-flash`), une piece par prompt avec un prefixe de style commun
(« paper craft cut-out puppet part … solid chroma green background ») et des couleurs fixees
(veste orange brule a liseré blanc, jean bleu marine, baskets blanches a semelle corail). Detourage par chroma key
numpy/scipy (distance au vert, erosion de frange, despill), alignement de l'axe principal par ACP, teinte du cou et de la
queue de cheval recalee sur la tete.

Touche S ou bouton « Squelette » : version non habillee (rendu procedural d'origine) + rig. Boucle de 16 s, bouton Rejouer.
`?t=11.2` fige le temps (captures), `?sk=1` force le squelette.

![course](course.png)
![recuperation](recuperation.png)

Rendu procedural d'origine (mode Squelette sans le rig) :

![marche](walk.png)
![course procedurale](run.png)
