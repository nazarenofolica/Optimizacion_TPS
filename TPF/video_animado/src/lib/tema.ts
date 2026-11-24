import { loadFont as cargarFredoka } from "@remotion/google-fonts/Fredoka";
import { loadFont as cargarMontserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as cargarInter } from "@remotion/google-fonts/Inter";

// Tipografías: Fredoka (redondeada, juguetona) para títulos y cifras; Montserrat para los subtítulos.
export const { fontFamily: TITULO } = cargarFredoka("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin", "latin-ext"],
});
export const { fontFamily: TEXTO } = cargarMontserrat("normal", {
  weights: ["600", "800", "900"],
  subsets: ["latin", "latin-ext"],
});

// Fredoka no trae griego ni símbolos matemáticos: las fórmulas caen a Inter (griego, ≤) y, para lo que falte (∈),
// a las fuentes matemáticas del sistema.
const { fontFamily: INTER } = cargarInter("normal", { weights: ["600", "700"], subsets: ["greek", "latin"] });
export const FORMULA = `${TITULO}, ${INTER}, "Cambria Math", "Segoe UI Symbol", serif`;

export const W = 1080;
export const H = 1920;
export const FPS = 30;

// Zona segura de Reels (1080x1920): arriba 220 px libres, nada debajo de 1470, a la derecha 100 px libres desde 1155.
export const ZONA = { arriba: 230, abajo: 1470, lado: 60 };
export const ESCENARIO = { y0: 330, y1: 1240 }; // donde vive la animación; abajo, los subtítulos

export const C = {
  fondo: "#FFF5E6",
  papel: "#FFFBF4",
  tinta: "#23213A",
  tintaSuave: "#6B6880",
  verde: "#22B07D",
  verdeClaro: "#D5F5E6",
  rojo: "#FF5A5F",
  rojoClaro: "#FFE1E2",
  amarillo: "#FFC93C",
  amarilloClaro: "#FFF0C2",
  azul: "#4D7CFE",
  azulClaro: "#DCE6FF",
  violeta: "#8E63F5",
  violetaClaro: "#EAE1FF",
  naranja: "#FF9A3C",
  sepia: "#EAD8B5",
  sepiaTinta: "#5B4630",
  blanco: "#FFFFFF",
};

export const SOMBRA = "0 18px 40px rgba(35,33,58,0.16)";
