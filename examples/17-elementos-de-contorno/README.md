# Ejemplo 17: elementos de contorno 2D

Todo es sintético. `python main.py [carpeta]` corre cuatro casos con `analyze_bem` (método de discontinuidad de
desplazamiento, medio elástico infinito, deformación plana, sin gravedad): (a) el DDM frente a Kirsch (errores en el
contorno y en el campo, K = 1 y 0,5); (b) una herradura con Hoek-Brown (GSI, mi, D); (c) dos tajeos con un pilar, con
una malla gruesa (aviso) y otra fina; (d) el caso del laboratorio de UBC. Imprime solo conteos y valores; las figuras
van a la carpeta indicada (por omisión, una temporal).

El factor de resistencia por omisión es el 3D de RS2; `sf_mode="examine2d"` da el 2D. Un SF menor que 1 marca
sobreesfuerzo, no la extensión de la falla. No reemplaza a RS2 ni a Examine2D.
