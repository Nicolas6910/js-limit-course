# js-limit-course

Cycle de marche puis course d'un personnage 2D entierement procedural (canvas 2D, aucun asset, aucune image generee).

- Rig articule : IK deux os pour les jambes, pieds ancres au sol en appui (zero glissement), deroule talon/pointe
- Allure pilotee par la vitesse : cadence, longueur de pas, facteur d'appui (62 % marche -> 31 % course, phase de vol)
- Poids : bassin en pendule inverse a la marche, ressort-masse a la course, contrainte de portee de jambe
- Anticipation (accroupi + recul avant le depart et avant la course), freinage avec pied pose en avant et buste en arriere, recuperation essoufflee
- Ressorts secondaires : buste, tete, bras, sac a dos, queue de cheval en Verlet
- Rue de nuit avec 7 plans de parallaxe et sol en perspective

Touche S ou bouton « Squelette » pour voir le rig. Boucle de 16 s, bouton Rejouer.

![marche](walk.png)
![course](run.png)
