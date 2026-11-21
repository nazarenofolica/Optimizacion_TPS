"use strict";
/*
 * Motor de la canasta saludable en el navegador. Es la misma lógica que el motor de Python (la referencia, con sus
 * tests): canasta/requerimientos.py (metas), oferta.py (restricciones, sucursales y oferta), modelo.py (el problema
 * de la dieta en dos etapas) y resultado.py (ticket, cobertura y comparación), con los datos y los parámetros que
 * exporta canasta/exportar.py y el mismo solver, HiGHS, compilado a WebAssembly. Las funciones llevan el nombre de su
 * par en Python. Corre en un Web Worker para que la página no se trabe mientras resuelve.
 */
(function () {
  const HIGHS_URL = "https://cdn.jsdelivr.net/npm/highs@1.15.4/build/";
  const EN_WORKER = typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope;
  const DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];
  const NUMERICAS = ["contenido", "unidades", "gramos_envase", "parte_comestible", "porcion_g", "precio_referencia_100g"];

  let D = null;   // datos del día
  let P = null;   // parámetros de canasta/config.py

  // ============================================================
  // Números y textos, como los formatea Python
  // ============================================================

  // f"{x:,.{d}f}" con punto de miles y coma decimal.
  function fmt(x, d = 0) {
    const a = Math.abs(x);
    let texto = a.toFixed(d);
    // Un empate exacto (1460,5 con d = 0; 0,25 con d = 1) Python lo redondea al par y toFixed hacia arriba. Con 30
    // decimales de más, el desarrollo exacto de un double de este tamaño ya terminó: un empate es "...5" y ceros.
    const largo = a.toFixed(Math.min(100, d + 30));
    const decimales = (largo.split(".")[1] || "").replace(/0+$/, "");
    if (decimales.length === d + 1 && decimales.endsWith("5")) {
      const truncado = largo.slice(0, largo.indexOf(".") + (d ? d + 1 : 0));
      if (Number(truncado.slice(-1)) % 2 === 0) texto = truncado;
    }
    const [entero, dec] = texto.split(".");
    const miles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (x < 0 && Number(texto) !== 0 ? "-" : "") + miles + (dec ? "," + dec : "");
  }

  // round(x, -1) de Python: a la decena, con los empates exactos al par.
  function redondearDecena(x) {
    const resto = x % 10;
    const base = x - resto;
    if (resto < 5) return base;
    if (resto > 5) return base + 10;
    return (base / 10) % 2 === 0 ? base : base + 10;
  }

  const redondear = (x, d) => { const f = 10 ** d; return Math.round(x * f) / f; };
  const comparar = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const minusc = (s) => s.toLowerCase();

  // ============================================================
  // Datos (canasta/exportar.py)
  // ============================================================

  // Base64 de un gzip (como lo escribe exportar.py) a bytes.
  async function desempacar(b64) {
    const binario = atob(b64.trim());
    const bytes = new Uint8Array(binario.length);
    for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
    const flujo = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(flujo).arrayBuffer();
  }

  async function cargarPaquete(meta64, binario64) {
    const meta = JSON.parse(new TextDecoder().decode(await desempacar(meta64)));
    cargarDatos(meta, await desempacar(binario64));
    return { fecha: D.fecha, perfiles: D.perfiles, parametros: P, productos: D.productos.n, tiendas: D.tiendas.id.length,
      productosTotal: D.productosTotal };
  }

  function cargarDatos(meta, buffer) {
    P = meta.parametros;
    const seccion = (nombre) => {
      const s = meta.binario[nombre];
      const Tipo = { f64: Float64Array, u32: Uint32Array, u16: Uint16Array, i32: Int32Array }[s.tipo];
      return new Tipo(buffer, s.desde, s.n);
    };
    const mp = meta.productos;
    const n = mp.id.length;
    const productos = { n, id: mp.id, granel: mp.granel, nombre: mp.nombre, marca: mp.marca, aptitud: seccion("p.aptitud") };
    for (const c of NUMERICAS.concat(meta.columnas_nutrientes)) productos[c] = seccion("p." + c);
    for (const c of ["subcategoria", "grupo_alimentario", "alimento_id", "unidad_contenido", "fuente_nutrientes"]) {
      const { valores, codigos } = mp[c];
      productos[c] = codigos.map((k) => (k < 0 ? null : valores[k]));
    }
    const aCocinar = new Set(P.ALIMENTOS_A_COCINAR);
    productos.a_cocinar = Uint8Array.from(productos.alimento_id, (a) => (aCocinar.has(a) ? 1 : 0));
    const agua = new Set(P.ALIMENTOS_AGUA);
    productos.es_agua = Uint8Array.from(productos.alimento_id, (a) => (agua.has(a) ? 1 : 0));

    // Los precios vienen por producto; se reordenan por tienda (y dentro, por producto, como en Python).
    const porProducto = seccion("precios.por_producto");
    const tienda = seccion("precios.tienda");
    const centavos = seccion("precios.centavos");
    const promocion = seccion("precios.promocion");
    const nT = meta.tiendas.id.length;
    const inicio = new Int32Array(nT + 1);
    for (let j = 0; j < tienda.length; j++) inicio[tienda[j] + 1]++;
    for (let t = 0; t < nT; t++) inicio[t + 1] += inicio[t];
    const cursor = inicio.slice(0, nT);
    const filaProd = new Int32Array(tienda.length);
    const filaPrecio = new Float64Array(tienda.length);
    const filaPromo = new Float64Array(tienda.length);
    let j = 0;
    for (let p = 0; p < n; p++) {
      for (let k = 0; k < porProducto[p]; k++, j++) {
        const pos = cursor[tienda[j]]++;
        filaProd[pos] = p;
        filaPrecio[pos] = centavos[j] / 100;
        filaPromo[pos] = promocion[j] ? promocion[j] / 100 : NaN;
      }
    }
    D = {
      fecha: meta.fecha_precios, productosTotal: meta.productos_total, productos, tiendas: meta.tiendas,
      precios: { inicio, filaProd, filaPrecio, filaPromo }, nombres: meta.nombres,
      requerimientos: meta.requerimientos, guias: meta.guias, perfiles: meta.perfiles, criterios: meta.criterios,
    };
  }

  // ============================================================
  // Requerimientos (canasta/requerimientos.py)
  // ============================================================

  function validar(p) {
    const errores = [];
    if (!["F", "M"].includes(p.sexo)) errores.push("El sexo tiene que ser F o M.");
    if (!(P.EDAD_MINIMA <= p.edad && p.edad <= P.EDAD_MAXIMA)) {
      errores.push(`La edad tiene que estar entre ${P.EDAD_MINIMA} y ${P.EDAD_MAXIMA} años (antes de los ` +
        `${P.EDAD_MINIMA}, la alimentación la indica el pediatra).`);
    }
    if (!(P.PESO_RANGO_KG[0] <= p.peso_kg && p.peso_kg <= P.PESO_RANGO_KG[1])) errores.push("El peso no es válido.");
    if (p.altura_cm != null && !(P.ALTURA_RANGO_CM[0] <= p.altura_cm && p.altura_cm <= P.ALTURA_RANGO_CM[1])) {
      errores.push("La altura no es válida.");
    }
    if (!(p.actividad in P.ACTIVIDAD)) errores.push(`Actividad desconocida: ${p.actividad}.`);
    if (!(p.objetivo in P.OBJETIVO)) errores.push(`Objetivo desconocido: ${p.objetivo}.`);
    if (!["general", "embarazo", "lactancia"].includes(p.etapa)) errores.push(`Etapa desconocida: ${p.etapa}.`);
    else if (p.etapa !== "general" && (p.sexo !== "F" || !(14 <= p.edad && p.edad <= 50))) {
      errores.push("Embarazo y lactancia aplican a mujeres de 14 a 50 años.");
    }
    if (p.etapa === "embarazo" && ![1, 2, 3].includes(p.trimestre)) errores.push("Falta el trimestre del embarazo (1, 2 o 3).");
    const desconocidas = p.restricciones.filter((r) => !(r in P.RESTRICCIONES));
    if (desconocidas.length) errores.push(`Restricciones desconocidas: ${desconocidas.join(", ")}.`);
    return errores;
  }

  const esMenor = (p) => p.edad < 18;
  const esVegetariana = (p) => p.restricciones.includes("vegetariano") || p.restricciones.includes("vegano");

  function pesoReferencia(p, pasos) {
    if (p.altura_cm == null || esMenor(p)) return p.peso_kg;
    const m = p.altura_cm / 100;
    const imc = p.peso_kg / m ** 2;
    const categoria = imc < 18.5 ? "bajo peso" : imc < 25 ? "normal" : imc < 30 ? "sobrepeso" : "obesidad";
    if (imc < P.IMC_OBESIDAD || p.etapa !== "general") {
      pasos.push({ titulo: "Índice de masa corporal",
        formula: `IMC = peso / altura² = ${fmt(p.peso_kg, 1)} / ${fmt(m, 2)}² = ${fmt(imc, 1)}`,
        resultado: `${fmt(imc, 1)} (${categoria}): se usa el peso real`, fuente: "OMS" });
      return p.peso_kg;
    }
    const ideal = P.IMC_REFERENCIA * m ** 2;
    const ajustado = ideal + P.FRACCION_EXCESO_PESO * (p.peso_kg - ideal);
    pasos.push({ titulo: "Índice de masa corporal y peso ajustado",
      formula: `IMC = ${fmt(p.peso_kg, 1)} / ${fmt(m, 2)}² = ${fmt(imc, 1)} (obesidad). Peso ajustado ` +
        `= peso con IMC 25 + 25 % del exceso = ${fmt(ideal, 1)} + 0,25 × (${fmt(p.peso_kg, 1)} − ${fmt(ideal, 1)})`,
      resultado: `${fmt(ajustado, 1)} kg para la energía y la proteína`,
      fuente: "Práctica clínica habitual (el peso real sobreestima el gasto con obesidad)" });
    return ajustado;
  }

  function energiaDia(p, peso, pasos, avisos) {
    const act = P.ACTIVIDAD[p.actividad];
    let energia;
    if (esMenor(p)) {
      const [c, a, b] = P.FAO_INFANTIL[p.sexo];
      const total = c + a * peso + b * peso ** 2;
      pasos.push({ titulo: "Gasto energético total (chicos y adolescentes, actividad moderada)",
        formula: `${fmt(c, 1)} + ${fmt(a, 1)} × ${fmt(peso, 1)} − ${fmt(-b, 3)} × ${fmt(peso, 1)}²`,
        resultado: `${fmt(total)} kcal/día`, fuente: "FAO/OMS/UNU 2004, Human energy requirements" });
      const ajustado = total * act.ajuste_infantil * (1 + P.CRECIMIENTO_INFANTIL);
      pasos.push({ titulo: "Actividad y crecimiento",
        formula: `${fmt(total)} × ${fmt(act.ajuste_infantil, 2)} (actividad ${minusc(act.nombre)}) × ` +
          `${fmt(1 + P.CRECIMIENTO_INFANTIL, 2)} (crecimiento)`,
        resultado: `${fmt(ajustado)} kcal/día`, fuente: "FAO/OMS/UNU 2004: ±15 % por actividad; ~2 % para el crecimiento" });
      energia = ajustado;
    } else {
      const [, , a, b] = P.SCHOFIELD[p.sexo].find(([d, h]) => d <= p.edad && p.edad < h);
      const reposo = a * peso + b;
      pasos.push({ titulo: "Gasto energético en reposo", formula: `${fmt(a, 3)} × ${fmt(peso, 1)} kg + ${fmt(b, 1)}`,
        resultado: `${fmt(reposo)} kcal/día`,
        fuente: `Ecuación de Schofield (FAO/OMS/UNU 2004) para ${p.sexo === "M" ? "varones" : "mujeres"} de su edad` });
      energia = reposo * act.pal;
      pasos.push({ titulo: "Nivel de actividad física",
        formula: `${fmt(reposo)} × PAL ${fmt(act.pal, 2)} (${minusc(act.nombre)}: ${minusc(act.descripcion)})`,
        resultado: `${fmt(energia)} kcal/día`,
        fuente: "FAO/OMS/UNU 2004 (sedentario 1,40-1,69; activo 1,70-1,99; vigoroso 2,00-2,40)" });
      const obj = P.OBJETIVO[p.objetivo];
      if (p.objetivo !== "mantener") {
        if (p.etapa !== "general") {
          avisos.push("En el embarazo y la lactancia no se busca bajar ni subir de peso: se mantiene.");
        } else if ("superavit_kcal" in obj) {
          const nueva = energia + obj.superavit_kcal;
          pasos.push({ titulo: `Objetivo: ${minusc(obj.nombre)}`,
            formula: `${fmt(energia)} + ${fmt(obj.superavit_kcal)} kcal de superávit`,
            resultado: `${fmt(nueva)} kcal/día`,
            fuente: "Superávit habitual para recuperar peso: 300 a 500 kcal/día (~0,25 a 0,5 kg por semana)" });
          energia = nueva;
          if (p.altura_cm != null && p.peso_kg / (p.altura_cm / 100) ** 2 >= P.IMC_SOBREPESO) {
            avisos.push("Con un IMC de sobrepeso no se recomienda aumentar de peso; consultá a un profesional.");
          }
        } else {
          const nueva = Math.max(energia * obj.factor, reposo * P.PISO_ENERGIA_REPOSO);
          pasos.push({ titulo: `Objetivo: ${minusc(obj.nombre)}`,
            formula: `${fmt(energia)} × ${fmt(obj.factor, 2)}` +
              (p.objetivo === "bajar" ? ` (no menos de ${fmt(P.PISO_ENERGIA_REPOSO, 1)} × el gasto en reposo)` : ""),
            resultado: `${fmt(nueva)} kcal/día`, fuente: "Déficit moderado (~15 %) o superávit chico (~10 %)" });
          energia = nueva;
        }
      }
    }
    if (p.etapa === "embarazo") {
      const extra = P.ENERGIA_EMBARAZO[String(p.trimestre)];
      pasos.push({ titulo: `Embarazo (${p.trimestre}.º trimestre)`, formula: `${fmt(energia)} + ${extra}`,
        resultado: `${fmt(energia + extra)} kcal/día`, fuente: "FAO/OMS/UNU 2004" });
      energia += extra;
    } else if (p.etapa === "lactancia") {
      const extra = P.ENERGIA_LACTANCIA;
      pasos.push({ titulo: "Lactancia", formula: `${fmt(energia)} + ${extra}`, resultado: `${fmt(energia + extra)} kcal/día`,
        fuente: "FAO/OMS/UNU 2004 (lactancia exclusiva, primeros 6 meses)" });
      energia += extra;
    }
    if (esMenor(p) && p.objetivo !== "mantener") {
      avisos.push("En chicos y adolescentes no se ajusta la energía para bajar o subir de peso: eso lo indica el pediatra.");
    }
    return redondearDecena(energia);
  }

  function proteinaGKg(p, pasos) {
    const base = P.PROTEINA_BASE.find(([d, h]) => d <= p.edad && p.edad <= h)[2];
    const motivos = [`${fmt(base, 2)} por la edad`];
    let valor = base;
    if (p.etapa === "embarazo" && [2, 3].includes(p.trimestre)) {
      valor = Math.max(valor, P.PROTEINA_EMBARAZO);
      motivos.push(`${fmt(P.PROTEINA_EMBARAZO, 1)} en el embarazo`);
    }
    if (p.etapa === "lactancia") {
      valor = Math.max(valor, P.PROTEINA_LACTANCIA);
      motivos.push(`${fmt(P.PROTEINA_LACTANCIA, 1)} en la lactancia`);
    }
    if (p.actividad in P.PROTEINA_ACTIVIDAD && !esMenor(p)) {
      valor = Math.max(valor, P.PROTEINA_ACTIVIDAD[p.actividad]);
      motivos.push(`${fmt(P.PROTEINA_ACTIVIDAD[p.actividad], 1)} por la actividad`);
    }
    if (p.etapa === "general" && !esMenor(p)) {
      if (p.objetivo === "subir") {
        valor = Math.max(valor, P.PROTEINA_SUBIR);
        motivos.push(`${fmt(P.PROTEINA_SUBIR, 1)} para ganar músculo`);
      } else if (p.objetivo === "bajar") {
        valor = Math.max(valor, P.PROTEINA_BAJAR);
        motivos.push(`${fmt(P.PROTEINA_BAJAR, 1)} al bajar de peso`);
      } else if (p.objetivo === "aumentar") {
        valor = Math.max(valor, P.PROTEINA_AUMENTAR);
        motivos.push(`${fmt(P.PROTEINA_AUMENTAR, 1)} para aumentar de peso`);
      }
    }
    pasos.push({ titulo: "Proteína por kg de peso", formula: "el mayor de: " + motivos.join("; "),
      resultado: `${fmt(valor, 2)} g por kg por día`,
      fuente: "NASEM (RDA), PROT-AGE/ESPEN (mayores de 65), ACSM e ISSN (deportistas)" });
    return valor;
  }

  function meta(clave, nombre, unidad, columna, minimo, maximo, extra = {}) {
    return { clave, nombre, unidad, columna, minimo, maximo, peso: P.PESO_DEFICIT_PREDETERMINADO, fuente: "",
      tipo: "nutriente", alimentos: null, grupo: null, medida: "g", semanal: false, nota: "", ...extra };
  }

  function filaEtapa(p, tipo) {
    const t = D.requerimientos.filter((f) => f.tipo === tipo);
    const etapas = p.etapa !== "general" ? [p.etapa, "general"] : ["general"];
    for (const etapa of etapas) {
      const fila = t.find((f) => Number(f.edad_desde) <= p.edad && Number(f.edad_hasta) >= p.edad
        && [p.sexo, "ambos"].includes(f.sexo) && f.etapa === etapa);
      if (fila) return fila;
    }
    throw new Error(`No hay ingestas de referencia (${tipo}) para ${p.sexo} de ${p.edad} años`);
  }

  function micronutrientes(p, pasos, avisos) {
    const minimos = filaEtapa(p, "minimo"), maximos = filaEtapa(p, "maximo");
    const columnas = Object.keys(minimos).filter((c) => !["tipo", "sexo", "edad_desde", "edad_hasta", "etapa"].includes(c));
    const etapa = { general: "", embarazo: ", embarazo", lactancia: ", lactancia" }[p.etapa];
    let grupo = `${p.sexo === "F" ? "mujeres" : "varones"} de ${minimos.edad_desde} a ${minimos.edad_hasta} años`;
    if (minimos.sexo === "ambos") grupo = `chicos de ${minimos.edad_desde} a ${minimos.edad_hasta} años`;
    pasos.push({ titulo: "Vitaminas y minerales", formula: `Ingestas de referencia para ${grupo}${etapa}`,
      resultado: "mínimos (RDA o AI) y máximos tolerables (UL) en la tabla de cobertura",
      fuente: "NASEM/IOM, Dietary Reference Intakes; sodio: OMS 2012" });
    const metas = [];
    for (const c of columnas) {
      let mn = minimos[c] ? Number(minimos[c]) : null;
      let mx = maximos[c] ? Number(maximos[c]) : null;
      if (mn === null && mx === null) continue;
      let nota = "";
      if (mn !== null && esVegetariana(p) && c in P.FACTOR_VEGETARIANO) {
        const f = P.FACTOR_VEGETARIANO[c];
        nota = `× ${fmt(f, 1)} por dieta vegetariana (menor absorción)`;
        mn *= f;
        // El mínimo ajustado no puede pasar el máximo tolerable (hierro de una embarazada vegetariana: 27 × 1,8 =
        // 48,6 mg contra 45 mg): se apunta al máximo y lo que falta lo indica un profesional, como suplemento.
        if (mx !== null && mn > mx) {
          avisos.push(`Con dieta vegetariana, el ${minusc(D.nombres[c][0])} que hace falta (${fmt(mn, 1)} ${D.nombres[c][1]}) ` +
            `supera el máximo tolerable (${fmt(mx, 1)} ${D.nombres[c][1]}): la canasta apunta al máximo y la diferencia ` +
            "se cubre con un suplemento indicado por un profesional.");
          nota += `; se limita al máximo tolerable (${fmt(mx, 1)})`;
          mn = mx;
        }
      }
      if (c === "sodio_mg" && p.restricciones.includes("hipertension")) {
        mx = Math.min(mx, P.SODIO_HIPERTENSION_MG);
        nota = "tope de 1.500 mg por hipertensión (AHA)";
      }
      let tipo = "nutriente";
      if (P.INFORMATIVAS.includes(c)) {
        tipo = "informativa";
        nota = "informativa: la mayor parte se sintetiza con el sol; no se le exige a la compra";
      }
      if (P.INFORMATIVAS_VEGANO.includes(c) && p.restricciones.includes("vegano")) {
        tipo = "informativa";
        nota = "informativa: solo está en alimentos de origen animal o fortificados; un vegano necesita suplemento";
        avisos.push("La vitamina B12 no se cubre con alimentos veganos comunes: hace falta un suplemento indicado por un profesional.");
      }
      const [nombre, unidad] = D.nombres[c];
      metas.push(meta(c, nombre, unidad, c, mn, mx, { nota, tipo,
        fuente: c !== "sodio_mg" ? "NASEM/IOM DRI" : "OMS 2012 / NASEM 2019" }));
    }
    return metas;
  }

  function macros(p, e, protG, pasos) {
    const grasas = esMenor(p) ? P.GRASAS_PCT_INFANTIL : P.GRASAS_PCT_ADULTO;
    const protMax = esMenor(p) ? P.PROTEINA_PCT_MAX_INFANTIL : P.PROTEINA_PCT_MAX_ADULTO;
    const diabetes = p.restricciones.includes("diabetes");
    const libres = diabetes ? P.AZUCARES_LIBRES_PCT_DIABETES : P.AZUCARES_LIBRES_PCT_MAX;
    const CH = P.CARBOHIDRATOS_PCT;
    const metas = [
      meta("energia_kcal", "Energía", "kcal", "energia_kcal", e * (1 - P.TOLERANCIA_ENERGIA), e * (1 + P.TOLERANCIA_ENERGIA),
        { tipo: "energia", fuente: "FAO/OMS/UNU 2004", nota: `meta ${fmt(e)} kcal ± ${fmt(P.TOLERANCIA_ENERGIA * 100)} %` }),
      meta("proteinas_g", "Proteínas", "g", "proteinas_g", protG, protMax / 100 * e / 4,
        { tipo: "macro", fuente: "NASEM; AMDR", nota: `hasta el ${fmt(protMax)} % de la energía` }),
      meta("carbohidratos_g", "Carbohidratos", "g", "carbohidratos_g", CH[0] / 100 * e / 4, CH[1] / 100 * e / 4,
        { tipo: "macro", fuente: "AMDR (NASEM 2005)", nota: `${fmt(CH[0])} a ${fmt(CH[1])} % de la energía` }),
      meta("grasas_totales_g", "Grasas totales", "g", "grasas_totales_g", grasas[0] / 100 * e / 9, grasas[1] / 100 * e / 9,
        { tipo: "macro", fuente: "AMDR (NASEM 2005)", nota: `${fmt(grasas[0])} a ${fmt(grasas[1])} % de la energía` }),
      meta("grasas_saturadas_g", "Grasas saturadas", "g", "grasas_saturadas_g", null, P.SATURADAS_PCT_MAX / 100 * e / 9,
        { tipo: "macro", fuente: "OMS 2023", nota: `menos del ${fmt(P.SATURADAS_PCT_MAX)} % de la energía` }),
      meta("grasas_trans_g", "Grasas trans", "g", "grasas_trans_g", null, P.TRANS_PCT_MAX / 100 * e / 9,
        { tipo: "macro", fuente: "OMS 2023", nota: `menos del ${fmt(P.TRANS_PCT_MAX)} % de la energía` }),
      meta("azucares_libres_g", "Azúcares libres (estimados)", "g", "azucares_libres_g", null, libres / 100 * e / 4,
        { tipo: "macro", fuente: "OMS 2015", nota: `menos del ${fmt(libres)} % de la energía` +
          (diabetes ? " por diabetes" : "") + "; se cuentan los azúcares de los productos con azúcar agregada" }),
      meta("fibra_g", "Fibra", "g", "fibra_g", P.FIBRA_G_POR_1000_KCAL * e / 1000, null,
        { tipo: "macro", fuente: "NASEM (AI)", nota: `${fmt(P.FIBRA_G_POR_1000_KCAL)} g cada 1.000 kcal` }),
    ];
    pasos.push({ titulo: "Macronutrientes",
      formula: `Proteínas ≥ ${fmt(protG)} g; carbohidratos ${fmt(CH[0])}-${fmt(CH[1])} % de la energía (÷ 4 kcal/g); grasas ` +
        `${fmt(grasas[0])}-${fmt(grasas[1])} % (÷ 9 kcal/g); saturadas < ${fmt(P.SATURADAS_PCT_MAX)} %; azúcares ` +
        `libres < ${fmt(libres)} %; fibra ${fmt(P.FIBRA_G_POR_1000_KCAL)} g cada 1.000 kcal`,
      resultado: `carbohidratos ${fmt(metas[2].minimo)}-${fmt(metas[2].maximo)} g; grasas ` +
        `${fmt(metas[3].minimo)}-${fmt(metas[3].maximo)} g; fibra ≥ ${fmt(metas[7].minimo)} g`,
      fuente: "NASEM 2005 (AMDR), OMS 2015 y 2023" });
    return metas;
  }

  function reglas(energia) {
    return D.guias.map((r) => {
      let cantidad = Number(r.cantidad);
      if (r.escala_energia === "si") cantidad *= energia / 2000;
      if (r.por === "semana") cantidad /= 7;
      let alimentos = null, grupo = null;
      if (r.alimentos.startsWith("grupo:")) grupo = r.alimentos.slice("grupo:".length);
      else alimentos = new Set(r.alimentos.split("|"));
      if (r.medida === "kcal_pct") cantidad = cantidad / 100 * energia;
      const unidad = { g: "g", porciones: "porciones", kcal_pct: "kcal" }[r.medida];
      const [mn, mx] = r.sentido === "min" ? [cantidad, null] : [null, cantidad];
      return meta(`regla_${r.regla}`, r.descripcion, unidad, null, mn, mx, { peso: P.PESO_DEFICIT.reglas,
        fuente: "Guías Alimentarias para la Población Argentina (2016)", tipo: "regla", alimentos, grupo,
        medida: r.medida, semanal: r.por === "semana" });
    });
  }

  // Meta de agua del día, en gramos (≈ ml). Con agua comprada se le exige a la compra; de la canilla, se informa.
  function aguaMeta(p, modo, pasos) {
    const m = P.AGUA_MODOS[modo];
    const total = m.cuenta === "total";
    const tabla = total ? P.AGUA_TOTAL_L : P.AGUA_BEBIDAS_L;
    let litros, grupo;
    if (p.etapa !== "general") {
      litros = tabla[p.etapa];
      grupo = p.etapa === "embarazo" ? "el embarazo" : "la lactancia";
    } else {
      const [d, h, l] = tabla[p.sexo].find(([d0, h0]) => d0 <= p.edad && p.edad <= h0);
      litros = l;
      const quienes = h <= 8 ? "chicos" : p.sexo === "F" ? "mujeres" : "varones";
      grupo = h >= P.EDAD_MAXIMA ? `${quienes} de ${d} años o más` : `${quienes} de ${d} a ${h} años`;
    }
    const cuenta = total ? "el agua de todo lo que come y toma (bebidas y alimentos)"
      : "solo el agua y la soda que se compran, sin la de los alimentos";
    const fuente = total ? "NASEM/IOM 2004, ingesta adecuada de agua total"
      : !esMenor(p) && p.etapa === "general" ? "Guías Alimentarias para la Población Argentina (2016): 8 vasos de agua segura por día"
        : "NASEM/IOM 2004, agua de las bebidas";
    const resultado = m.compra ? `${fmt(litros, 1)} L por día` : `${fmt(litros, 1)} L por día, de la canilla (no se compra)`;
    const tipo = m.compra ? "nutriente" : "informativa";
    const nota = m.compra ? `cuenta ${cuenta}` : "informativa: el agua es la de la canilla; se muestra cuánta aportan los alimentos";
    pasos.push({ titulo: "Agua", formula: `Para ${grupo}; cuenta ${cuenta}`, resultado, fuente });
    if (total) return meta("agua", "Agua", "ml", "agua_g", litros * 1000, null, { tipo, fuente, nota });
    return meta("agua", "Agua (bebidas)", "ml", null, litros * 1000, null,
      { tipo, fuente, nota, alimentos: new Set(P.ALIMENTOS_AGUA), medida: "g" });
  }

  // agua: cómo toma agua el hogar (una clave de AGUA_MODOS).
  function calcular(p, agua = P.AGUA_MODO_PREDETERMINADO) {
    const errores = validar(p);
    if (!(agua in P.AGUA_MODOS)) errores.push(`Modo de agua desconocido: ${agua}.`);
    if (errores.length) throw new Error(errores.join(" "));
    const pasos = [], avisos = [];
    const peso = pesoReferencia(p, pasos);
    const energia = energiaDia(p, peso, pasos, avisos);
    const gKg = proteinaGKg(p, pasos);
    const prot = gKg * peso;
    pasos.push({ titulo: "Proteína del día", formula: `${fmt(gKg, 2)} g/kg × ${fmt(peso, 1)} kg`,
      resultado: `${fmt(prot)} g/día`, fuente: "" });
    const metas = macros(p, energia, prot, pasos).concat(micronutrientes(p, pasos, avisos), [aguaMeta(p, agua, pasos)],
      reglas(energia));
    if (p.restricciones.includes("diabetes") || p.restricciones.includes("hipertension")) {
      avisos.push("Con diabetes o hipertensión, esta canasta es orientativa: el plan lo ajusta el médico o un nutricionista.");
    }
    return { persona: p, energia_kcal: energia, proteina_g_kg: gKg, peso_referencia_kg: peso, metas, pasos, avisos };
  }

  // ============================================================
  // Oferta (canasta/oferta.py)
  // ============================================================

  function criterios(restricciones) {
    return restricciones.map((r) => ({ clave: r, nombre: P.RESTRICCIONES[r], criterio: D.criterios[r] }));
  }

  // Máscara de productos aptos y, por restricción, cuántos deja afuera (las aptitudes vienen evaluadas por Python).
  // conAgua: si el agua y la soda envasadas se consideran (solo si el hogar compra el agua).
  function aptos(restricciones, conAgua = true) {
    const pr = D.productos;
    const orden = Object.keys(P.RESTRICCIONES);
    const apto = new Uint8Array(pr.n).fill(1);
    if (!conAgua) for (let i = 0; i < pr.n; i++) if (pr.es_agua[i]) apto[i] = 0;
    const efecto = [];
    for (const r of restricciones) {
      const bit = 1 << orden.indexOf(r);
      let excluye = 0;
      for (let i = 0; i < pr.n; i++) {
        const m = (pr.aptitud[i] & bit) !== 0;
        if (apto[i] && !m) { excluye++; apto[i] = 0; }
      }
      efecto.push({ clave: r, nombre: P.RESTRICCIONES[r], excluye });
    }
    return { apto, efecto };
  }

  function distanciaKm(lat1, lon1, lat2, lon2) {
    const r = 6371.0, rad = Math.PI / 180;
    const f1 = lat1 * rad, f2 = lat2 * rad, df = f2 - f1, dl = (lon2 - lon1) * rad;
    const a = Math.sin(df / 2) ** 2 + Math.cos(f1) * Math.cos(f2) * Math.sin(dl / 2) ** 2;
    return 2 * r * Math.asin(Math.sqrt(a));
  }

  // La más cercana de cada cadena dentro del radio y, si faltan, las que siguen.
  function sucursalesCercanas(lat, lon, n = P.SUCURSALES_A_EVALUAR, radioKm = P.RADIO_KM) {
    const T = D.tiendas;
    const todas = T.id.map((_, i) => ({ i, d: distanciaKm(lat, lon, T.lat[i], T.lon[i]) }));
    todas.sort((a, b) => a.d - b.d);       // estable: los empates quedan en el orden de dim_tienda
    let radio = radioKm;
    let cerca = todas.filter((x) => x.d <= radio);
    while (cerca.length < n && radio < P.RADIO_MAXIMO_KM) {
      radio = Math.min(radio * 2, P.RADIO_MAXIMO_KM);
      cerca = todas.filter((x) => x.d <= radio);
    }
    return unaPorCadenaPrimero(cerca, n).sort((a, b) => a.d - b.d);
  }

  // La primera de cada cadena (en el orden de la lista) y, si faltan, las que siguen; a lo sumo n.
  function unaPorCadenaPrimero(lista, n) {
    const T = D.tiendas, vistas = new Set(), primeras = [], resto = [];
    for (const x of lista) {
      const bandera = T.bandera[x.i];
      if (vistas.has(bandera)) resto.push(x); else { vistas.add(bandera); primeras.push(x); }
    }
    return primeras.concat(resto).slice(0, n);
  }

  // Búsqueda por tiempo caminando (canasta/oferta.py: candidatas_caminando y sucursales_por_tiempo).
  const radioCaminataKm = (minutos) => minutos / 60 * P.VELOCIDAD_CAMINATA_KMH;
  const minutosEstimados = (km) => km * P.FACTOR_DESVIO_CAMINATA / P.VELOCIDAD_CAMINATA_KMH * 60;

  function porDistancia(lat, lon) {
    const T = D.tiendas;
    const todas = T.id.map((_, i) => ({ i, d: distanciaKm(lat, lon, T.lat[i], T.lon[i]) }));
    return todas.sort((a, b) => a.d - b.d);
  }

  // Las que se mandan al servicio de rutas: dentro del radio en línea recta, la más cercana de cada cadena primero.
  function candidatasCaminando(lat, lon, minutos, n = P.CANDIDATAS_MAXIMAS_RUTEO) {
    const T = D.tiendas, radio = radioCaminataKm(minutos);
    return unaPorCadenaPrimero(porDistancia(lat, lon).filter((x) => x.d <= radio), n).sort((a, b) => a.d - b.d)
      .map((x) => ({ id: T.id[x.i], lat: T.lat[x.i], lon: T.lon[x.i], distancia_km: x.d,
        minutos_estimados: minutosEstimados(x.d) }));
  }

  // tiempos: {id_tienda: {minutos, metros, fuente}}. Las n a evaluar entre las que están dentro del límite.
  function sucursalesPorTiempo(lat, lon, tiempos, limite, n = P.SUCURSALES_A_EVALUAR_CAMINATA) {
    const T = D.tiendas;
    const orden = (a, b) => a.minutos - b.minutos || a.d - b.d;
    const dentro = porDistancia(lat, lon).filter((x) => T.id[x.i] in tiempos)
      .map((x) => ({ ...x, ...tiempos[T.id[x.i]], minutos: Number(tiempos[T.id[x.i]].minutos) }))
      .filter((x) => x.minutos <= limite).sort(orden);
    return unaPorCadenaPrimero(dentro, n).sort(orden);
  }

  const caminata = (x) => (x.minutos === undefined ? { minutos: null, metros: null, fuente_tiempo: null }
    : { minutos: x.minutos, metros: x.metros ?? null, fuente_tiempo: x.fuente || "ruta" });

  // Esas sucursales (por id), con su distancia desde el lugar, de la más cercana a la más lejana.
  function sucursalesPorId(lat, lon, ids) {
    const T = D.tiendas, quiero = new Set(ids);
    return porDistancia(lat, lon).filter((x) => quiero.has(T.id[x.i]));
  }

  // Las sucursales de la lista (sin A) a las que se llega caminando desde A en a lo sumo minutosMax (estimado con la
  // línea recta), con kmDesdeA y minutosDesdeA; de la más cercana a A a la más lejana y, a igual distancia, por id.
  function vecinasDe(lista, a, minutosMax) {
    const T = D.tiendas;
    return lista.filter((x) => x.i !== a.i).map((x) => {
      const km = distanciaKm(T.lat[a.i], T.lon[a.i], T.lat[x.i], T.lon[x.i]);
      return { ...x, kmDesdeA: km, minutosDesdeA: minutosEstimados(km) };
    }).filter((x) => x.minutosDesdeA <= minutosMax)
      .sort((x, y) => x.minutosDesdeA - y.minutosDesdeA || comparar(T.id[x.i], T.id[y.i]));
  }

  // A lo sumo n de las vecinas (ordenadas por cercanía a A): la más cercana de cada otra cadena primero, después la de
  // la cadena de A y, si faltan, las que siguen. En el orden de las vecinas.
  function elegirVecinas(v, banderaA, n) {
    const T = D.tiendas;
    const elegidas = new Set(unaPorCadenaPrimero(v.filter((x) => T.bandera[x.i] !== banderaA)
      .concat(v.filter((x) => T.bandera[x.i] === banderaA)), n));
    return v.filter((x) => elegidas.has(x));
  }

  function podar(filas) {
    // filas: [{pos, sub, p100, pc}] en el orden de la oferta; devuelve las posiciones que quedan.
    const quedan = new Set();
    const porSub = (ordenadas, k) => {
      const cuenta = new Map();
      for (const f of ordenadas) {
        const c = cuenta.get(f.sub) || 0;
        if (c < k) { quedan.add(f.pos); cuenta.set(f.sub, c + 1); }
      }
    };
    porSub([...filas].sort((a, b) => a.p100 - b.p100 || a.pos - b.pos), P.PRODUCTOS_POR_SUBCATEGORIA);
    porSub([...filas].sort((a, b) => a.pc - b.pc || a.pos - b.pos), 1);
    return quedan;
  }

  // Productos de la sucursal que le sirven a alguien del hogar y, para cada persona, cuáles son aptos para ella.
  function ofertaTienda(t, aptosPersonas) {
    const pr = D.productos, { inicio, filaProd, filaPrecio, filaPromo } = D.precios;
    const filas = [];
    for (let j = inicio[t]; j < inicio[t + 1]; j++) {
      const p = filaProd[j];
      if (!aptosPersonas.some((a) => a[p])) continue;
      const granel = pr.granel[p];
      const precio = filaPrecio[j];
      const gramosCompra = granel ? P.PASO_GRANEL_G : pr.gramos_envase[p];
      const precioCompra = granel ? precio * P.PASO_GRANEL_G / 1000 : precio;
      const gc = gramosCompra * pr.parte_comestible[p];
      if (!(gc > 0 && precioCompra > 0)) continue;
      const p100 = precioCompra / gc * 100;
      if (!(p100 >= P.FRACCION_PRECIO_MINIMO * pr.precio_referencia_100g[p])) continue;
      filas.push({ p, precio, promo: filaPromo[j], granel, gramosCompra, precioCompra, gc, p100 });
    }
    const quedan = new Uint8Array(filas.length);
    for (const apto of aptosPersonas) {
      const propias = [];
      filas.forEach((f, pos) => { if (apto[f.p]) propias.push({ pos, sub: pr.subcategoria[f.p], p100: f.p100, pc: f.precioCompra }); });
      for (const pos of podar(propias)) quedan[pos] = 1;
    }
    const oferta = filas.filter((_, pos) => quedan[pos]);
    return { oferta, porPersona: aptosPersonas.map((a) => oferta.map((f) => a[f.p] === 1)) };
  }

  // ============================================================
  // Modelo (canasta/modelo.py)
  // ============================================================

  function coeficientes(filasProd, m) {
    const pr = D.productos;
    if (m.columna !== null) return filasProd.map((p) => pr[m.columna][p] / 100);
    return filasProd.map((p) => {
      const cuenta = m.grupo !== null ? pr.grupo_alimentario[p] === m.grupo : m.alimentos.has(pr.alimento_id[p]);
      if (!cuenta) return 0;
      if (m.medida === "g") return 1;
      if (m.medida === "porciones") return 1 / Math.max(pr.porcion_g[p], 1);
      return pr.energia_kcal[p] / 100;
    });
  }

  function deficitRelativo(m, valor) {
    const falta = m.minimo ? Math.max(0, 1 - valor / m.minimo) : 0;
    const sobra = m.maximo ? Math.max(0, valor / m.maximo - 1) : 0;
    return Math.max(falta, sobra);
  }

  const topePorPorciones = (porcion, energia) => P.PORCIONES_MAX_POR_ALIMENTO * porcion * Math.max(1, energia / 2000);

  // Tope por subcategoría: el de las porciones y, para el agua y la soda (aguaSub), la meta de agua del día si se le
  // exige a la compra (dos vasos no alcanzan).
  function topeVariedad(req, porcionSub, aguaSub) {
    const agua = req.metas.find((m) => m.clave === "agua" && m.tipo !== "informativa");
    return porcionSub.map((pz, s) => {
      const tope = topePorPorciones(pz, req.energia_kcal);
      return agua && aguaSub[s] ? Math.max(tope, agua.minimo) : tope;
    });
  }

  // ---- HiGHS (WebAssembly). Se baja y se compila una sola vez (una promesa compartida: la precarga y el primer
  // cálculo pueden pedirlo a la vez). Las sucursales se resuelven en paralelo en un grupo de workers de solver, uno por
  // núcleo (hasta 4), que reciben el módulo ya compilado; si el navegador no permite workers anidados, se resuelve acá.
  const MAX_SOLVERS = 4;
  let preparacion = null, highs = null, grupo = null;

  async function cargarScript(url) {
    if (EN_WORKER) { importScripts(url); return; }
    await new Promise((ok, mal) => {
      const s = document.createElement("script");
      s.src = url; s.onload = ok; s.onerror = () => mal(new Error(`No se pudo cargar ${url}`));
      document.head.appendChild(s);
    });
  }

  function prepararHighs() {
    if (!preparacion) {
      preparacion = (async () => {
        const r = await fetch(HIGHS_URL + "highs.wasm");
        if (!r.ok) throw new Error("No se pudo descargar el solver (HiGHS): revisá la conexión a internet.");
        return WebAssembly.compile(await r.arrayBuffer());
      })();
      preparacion.catch(() => { preparacion = null; });      // si falló la red, el próximo intento vuelve a bajarlo
    }
    return preparacion;
  }

  function instanciar(fabrica, compilado) {
    return new Promise((ok, mal) => {
      fabrica({
        instantiateWasm: (imports, listo) => {
          WebAssembly.instantiate(compilado, imports).then((inst) => listo(inst, compilado), mal);
          return {};
        },
      }).then(ok, mal);
    });
  }

  // Código de cada worker de solver: recibe el módulo compilado y resuelve los textos LP que le llegan.
  const CODIGO_SOLVER = `
    importScripts("${HIGHS_URL}highs.js");
    let compilado = null, highs = null;
    const instanciar = () => new Promise((ok, mal) => {
      Module({ instantiateWasm: (imports, listo) => {
        WebAssembly.instantiate(compilado, imports).then((i) => listo(i, compilado), mal); return {}; } }).then(ok, mal);
    });
    onmessage = async (e) => {
      if (e.data.modulo) { compilado = e.data.modulo; return; }
      const { id, texto, opciones } = e.data;
      for (let intento = 0; intento < 2; intento++) {
        try {
          if (!highs || intento > 0) highs = await instanciar();
          postMessage({ id, solucion: highs.solve(texto, opciones) });
          return;
        } catch (err) {
          if (intento > 0) postMessage({ id, solucion: { Status: "Error", error: String(err) } });
        }
      }
    };`;

  async function grupoDeSolvers() {
    if (grupo !== null) return grupo;
    const compilado = await prepararHighs();
    if (grupo !== null) return grupo;                         // otro pedido lo armó mientras se compilaba
    try {
      if (!EN_WORKER || typeof Worker === "undefined") throw new Error("en la página se resuelve en línea");
      const nucleos = (self.navigator && navigator.hardwareConcurrency) || 2;
      const n = Math.max(1, Math.min(MAX_SOLVERS, nucleos - 1));
      const url = URL.createObjectURL(new Blob([CODIGO_SOLVER], { type: "text/javascript" }));
      let siguiente = 0;
      const pendientes = new Map();
      const workers = Array.from({ length: n }, () => {
        const w = new Worker(url);
        w.carga = 0;
        w.onmessage = (e) => {
          const listo = pendientes.get(e.data.id);
          pendientes.delete(e.data.id);
          w.carga--;
          listo(e.data.solucion);
        };
        w.onerror = (e) => {
          e.preventDefault();
          for (const [id, listo] of pendientes) { pendientes.delete(id); listo({ Status: "Error", error: "el solver se interrumpió" }); }
        };
        w.postMessage({ modulo: compilado });
        return w;
      });
      grupo = {
        tamano: n,
        resolver: (texto, opciones) => new Promise((ok) => {
          const w = workers.reduce((a, b) => (b.carga < a.carga ? b : a));
          const id = ++siguiente;
          w.carga++;
          pendientes.set(id, ok);
          w.postMessage({ id, texto, opciones });
        }),
      };
    } catch (err) {
      grupo = false;                                         // se resuelve en este mismo hilo
    }
    return grupo;
  }

  async function instanciaHighs(nueva = false) {
    if (!highs || nueva) {
      await cargarScript(HIGHS_URL + "highs.js");
      highs = await instanciar((EN_WORKER ? self : window).Module, await prepararHighs());
    }
    return highs;
  }

  async function resolverLP(texto, opciones) {
    const g = await grupoDeSolvers();
    if (g) return g.resolver(texto, opciones);
    for (let intento = 0; intento < 2; intento++) {
      try {
        return (await instanciaHighs(intento > 0)).solve(texto, opciones);
      } catch (err) {
        if (intento > 0) return { Status: "Error", error: String(err) };
      }
    }
  }

  // Texto en formato LP (CPLEX) para HiGHS.
  function textoLP(objetivo, filas, cotas, enteras) {
    const num = (v) => String(Math.abs(v));
    const expr = (terminos) => {
      const partes = [];
      for (const [nombre, coef] of terminos) {
        if (coef === 0) continue;
        partes.push(`${coef < 0 ? "-" : "+"} ${num(coef)} ${nombre}`);
      }
      const lineas = [];
      for (let i = 0; i < partes.length; i += 8) lineas.push(partes.slice(i, i + 8).join(" "));
      return lineas.join("\n   ");
    };
    const salida = ["Minimize", " obj: " + expr(objetivo), "Subject To"];
    filas.forEach((f, i) => {
      const e = expr(f.terminos);
      if (e) salida.push(` r${i}: ${e} ${f.op} ${f.rhs}`);
    });
    salida.push("Bounds");
    for (const [nombre, lo, hi] of cotas) if (hi !== Infinity) salida.push(` ${lo} <= ${nombre} <= ${hi}`);
    if (enteras.length) {
      salida.push("General");
      for (let i = 0; i < enteras.length; i += 10) salida.push(" " + enteras.slice(i, i + 10).join(" "));
    }
    salida.push("End");
    return salida.join("\n");
  }

  function bloque(req, oferta, apto, subCodigos, porcionSub, aguaSub) {
    const columnas = [];
    apto.forEach((a, pos) => { if (a) columnas.push(pos); });
    const prods = columnas.map((pos) => oferta[pos].p);
    const metas = [], sinOferta = [];
    for (const m of req.metas) {
      const a = coeficientes(prods, m);
      if (m.tipo === "regla" && m.minimo !== null && !a.some((v) => v !== 0)) { sinOferta.push(m); continue; }
      metas.push([m, a]);
    }
    const energia = metas.find(([m]) => m.tipo === "energia");
    const filas = [];
    for (const [m, a] of metas) {
      if (m.tipo === "energia" || m.tipo === "informativa") continue;
      if (m.minimo !== null && m.minimo > 0) filas.push({ a: a.map((v) => v / m.minimo), signo: 1, peso: m.peso });
      if (m.maximo !== null) filas.push({ a: a.map((v) => v / m.maximo), signo: -1, peso: m.peso });
    }
    return { columnas, metas, sinOferta, filas, energia: energia[0], eCoef: energia[1],
      subCol: columnas.map((pos) => subCodigos[pos]), topeVar: topeVariedad(req, porcionSub, aguaSub) };
  }

  function sinSolucion(mensaje, oferta, bloques, inicio) {
    const n = oferta.length;
    return { estado: "sin_solucion", mensaje, oferta, compra: new Float64Array(n), costo: NaN, segundos: (Date.now() - inicio) / 1000,
      dietas: bloques.map((b) => ({ metas: b.metas.map(([m]) => m), valores: b.metas.map(() => 0), deficit: b.metas.map(() => 0),
        consumo: new Float64Array(n), reglasSinOferta: b.sinOferta })) };
  }

  async function resolver(personas, oferta, dias) {
    const inicio = Date.now();
    const n = oferta.length;
    const pr = D.productos;
    const subs = [...new Set(oferta.map((f) => pr.subcategoria[f.p]))].sort(comparar);
    const indiceSub = new Map(subs.map((s, i) => [s, i]));
    const subCodigos = oferta.map((f) => indiceSub.get(pr.subcategoria[f.p]));
    const porcionSub = subs.map(() => -Infinity);
    oferta.forEach((f, pos) => { porcionSub[subCodigos[pos]] = Math.max(porcionSub[subCodigos[pos]], pr.porcion_g[f.p]); });
    const aguaSub = subs.map(() => false);
    oferta.forEach((f, pos) => { if (pr.es_agua[f.p]) aguaSub[subCodigos[pos]] = true; });
    const bloques = personas.map(([req, apto]) => bloque(req, oferta, apto, subCodigos, porcionSub, aguaSub));
    if (bloques.some((b) => b.columnas.length === 0)) {
      return sinSolucion("La sucursal no vende alimentos aptos para alguien del hogar", oferta, bloques, inicio);
    }

    // Columnas c (persona, producto) y filas de metas, numeradas para todo el hogar.
    const producto = [], filas = [];
    let nc = 0;
    bloques.forEach((b) => {
      b.desde = nc;
      b.columnas.forEach((pos) => producto.push(pos));
      b.filas.forEach((f) => filas.push({ ...f, desde: nc, n: b.columnas.length }));
      nc += b.columnas.length;
    });
    const k = filas.length;
    const gc = oferta.map((f) => f.gc), precio = oferta.map((f) => f.precioCompra);
    const precioG = precio.map((v, i) => v / gc[i]);
    const ordenados = [...precioG].sort((a, b) => a - b);
    const mediana = ordenados.length % 2 ? ordenados[(ordenados.length - 1) / 2]
      : (ordenados[ordenados.length / 2 - 1] + ordenados[ordenados.length / 2]) / 2;
    const escala = mediana * 1500 || 1;

    // Filas comunes a las dos etapas, sobre las columnas c que entran (cc) y los déficits.
    const filasModelo = (cc) => {
      const salida = [];
      filas.forEach((f, r) => {
        const terminos = [];
        for (let j = 0; j < f.n; j++) if (cc[f.desde + j]) terminos.push([`c${f.desde + j}`, f.a[j]]);
        terminos.push([`d${r}`, f.signo]);
        salida.push(f.signo > 0 ? { terminos, op: ">=", rhs: 1 } : { terminos, op: "<=", rhs: 1 });
      });
      for (const b of bloques) {
        const terminos = [];
        b.columnas.forEach((_, j) => { if (cc[b.desde + j]) terminos.push([`c${b.desde + j}`, b.eCoef[j]]); });
        salida.push({ terminos, op: "<=", rhs: b.energia.maximo }, { terminos, op: ">=", rhs: b.energia.minimo });
        const porSub = new Map();
        b.columnas.forEach((_, j) => {
          if (!cc[b.desde + j]) return;
          const s = b.subCol[j];
          if (!porSub.has(s)) porSub.set(s, []);
          porSub.get(s).push([`c${b.desde + j}`, 1]);
        });
        for (const [s, terminos2] of porSub) salida.push({ terminos: terminos2, op: "<=", rhs: b.topeVar[s] });
      }
      return salida;
    };

    // --- Etapa 1: lo mejor que se puede cumplir.
    const todasC = new Uint8Array(nc).fill(1);
    const objetivo1 = producto.map((pos, j) => [`c${j}`, 1e-3 * precioG[pos] / escala])
      .concat(filas.map((f, r) => [`d${r}`, f.peso]));
    const cotasD = (tope) => filas.map((f, r) => [`d${r}`, 0, tope[r]]);
    const lp1 = await resolverLP(textoLP(objetivo1, filasModelo(todasC), cotasD(filas.map((f) => (f.signo > 0 ? 1 : Infinity))), []), {});
    if (lp1.Status !== "Optimal") {
      return sinSolucion("La sucursal no tiene alimentos aptos suficientes para llegar a la energía del día", oferta, bloques, inicio);
    }
    const dEstrella = filas.map((_, r) => lp1.Columns[`d${r}`].Primal);

    // --- Etapa 2: la compra más barata.
    const topeHogar = subs.map(() => 0);
    for (const b of bloques) b.topeVar.forEach((v, s) => { topeHogar[s] += v; });
    const xMax = oferta.map((_, pos) => Math.ceil(dias * topeHogar[subCodigos[pos]] / gc[pos]) + 1);
    const topeDef = filas.map((f, r) => Math.min(dEstrella[r] + P.HOLGURA_DEFICIT, f.signo > 0 ? 1 : Infinity));
    const mediaPrecio = precio.reduce((s, v) => s + v, 0) / n;

    const comprar = async (cols, entera) => {
      const cc = Uint8Array.from(producto, (pos) => cols[pos]);
      // Alguien sin columnas no puede llegar a su energía (en Python, la fila vacía hace infactible el modelo).
      if (bloques.some((b) => !b.columnas.some((_, j) => cc[b.desde + j]))) return { sol: { Status: "Infeasible" }, ok: false, cc };
      const filas2 = filasModelo(cc);
      const porProducto = new Map();
      producto.forEach((pos, j) => {
        if (!cc[j]) return;
        if (!porProducto.has(pos)) porProducto.set(pos, []);
        porProducto.get(pos).push([`c${j}`, dias]);
      });
      for (const [pos, terminos] of porProducto) filas2.push({ terminos: terminos.concat([[`x${pos}`, -gc[pos]]]), op: "<=", rhs: 0 });
      const xs = [];
      for (let pos = 0; pos < n; pos++) if (cols[pos]) xs.push(pos);
      const objetivo2 = xs.map((pos) => [`x${pos}`, precio[pos]]).concat(filas.map((f, r) => [`d${r}`, 1e-6 * mediaPrecio * f.peso]));
      const cotas = xs.map((pos) => [`x${pos}`, 0, xMax[pos]]).concat(cotasD(topeDef));
      const opciones = entera ? { mip_rel_gap: P.GAP_RELATIVO, time_limit: P.TIEMPO_MAXIMO_S } : {};
      const sol = await resolverLP(textoLP(objetivo2, filas2, cotas, entera ? xs.map((pos) => `x${pos}`) : []), opciones);
      const ok = sol.Status === "Optimal" || (sol.Status === "Time limit reached" && Number.isFinite(sol.ObjectiveValue));
      return { sol, ok, cc };
    };

    const todos = new Uint8Array(n).fill(1);
    const relajada = await comprar(todos, false);
    let cols = todos;
    if (relajada.ok) {
      const usadas = new Set();
      producto.forEach((pos, j) => { if (relajada.cc[j] && relajada.sol.Columns[`c${j}`].Primal > 1e-6) usadas.add(subCodigos[pos]); });
      cols = Uint8Array.from(subCodigos, (s) => (usadas.has(s) ? 1 : 0));
    }
    let res = await comprar(cols, true);
    if (!res.ok && cols.some((v) => !v)) {
      cols = todos;
      res = await comprar(cols, true);
    }
    if (!res.ok) return sinSolucion(`El modelo entero no encontró solución (${res.sol.Status}${res.sol.error ? ": " + res.sol.error : ""})`, oferta, bloques, inicio);

    const cTodas = new Float64Array(nc);
    producto.forEach((_, j) => {
      if (!res.cc[j]) return;
      const v = Math.max(res.sol.Columns[`c${j}`].Primal, 0);
      cTodas[j] = v < 0.05 ? 0 : v;           // restos numéricos del solver
    });
    const compra = new Float64Array(n);
    for (let pos = 0; pos < n; pos++) if (cols[pos]) compra[pos] = Math.round(res.sol.Columns[`x${pos}`].Primal);
    const dietas = bloques.map((b) => {
      const consumo = new Float64Array(n);
      b.columnas.forEach((pos, j) => { consumo[pos] = cTodas[b.desde + j]; });
      const valores = b.metas.map(([, a]) => b.columnas.reduce((s, pos, j) => s + a[j] * consumo[pos], 0));
      return { metas: b.metas.map(([m]) => m), valores, deficit: b.metas.map(([m], i) => deficitRelativo(m, valores[i])),
        consumo, reglasSinOferta: b.sinOferta };
    });
    const costo = precio.reduce((s, v, pos) => s + v * compra[pos], 0);
    return { estado: res.sol.Status === "Optimal" ? "optima" : "factible", mensaje: res.sol.Status, oferta, compra,
      dietas, costo, segundos: (Date.now() - inicio) / 1000 };
  }

  // ============================================================
  // Resultado (canasta/resultado.py)
  // ============================================================

  function cantidad(f, x) {
    const pr = D.productos, p = f.p;
    if (f.granel) return `${fmt(x * P.PASO_GRANEL_G / 1000, 3)} kg`;
    const contenido = pr.contenido[p];
    const u = pr.unidad_contenido[p];
    const unidad = { g: "g", ml: "ml" }[u] ?? (u || "");
    const uds = pr.unidades[p];
    const hayUnidades = !Number.isNaN(uds) && uds && uds > 1;
    // Se vende por unidad (frutas, ajo): no hay peso del envase que mostrar.
    if (contenido == null || Number.isNaN(contenido)) return `${fmt(x)} × ` + (hayUnidades ? `${fmt(uds)} u.` : "unidad");
    let envase;
    if (unidad === "g" && contenido >= 1000) envase = `${fmt(contenido / 1000, contenido % 1000 ? 3 : 0)} kg`;
    else if (unidad === "ml" && contenido >= 1000) envase = `${fmt(contenido / 1000, contenido % 1000 ? 2 : 0)} l`;
    else envase = `${fmt(contenido)} ${unidad}`.trim();
    if (hayUnidades) {
      const unidades = `${fmt(uds)} u.`;
      envase = pr.subcategoria[p] === "Huevos" ? unidades : `${envase} (${unidades})`;
    }
    return `${fmt(x)} × ${envase}`;
  }

  // Cantidad comestible: en litros (g ≈ ml) si es agua.
  const gramosTexto = (g, agua = false) => (agua ? (g >= 1000 ? `${fmt(g / 1000, 2)} l` : `${fmt(g)} ml`)
    : g >= 1000 ? `${fmt(g / 1000, 2)} kg` : `${fmt(g)} g`);

  function horarioHoy(t) {
    const hoy = (new Date().getDay() + 6) % 7;
    const h = D.tiendas.horarios[t][hoy];
    return { dia: DIAS_SEMANA[hoy].replace("miercoles", "miércoles").replace("sabado", "sábado"),
      horario: h === null ? "no informado" : h || "cerrado" };
  }

  const sinOfertaReal = (dieta, sinAptos) => dieta.reglasSinOferta.filter((m) => !sinAptos.has(m.clave));

  function puntaje(sol, sinAptos) {
    let total = 0;
    sol.dietas.forEach((dieta, i) => {
      dieta.metas.forEach((m, k) => { if (m.tipo !== "energia" && m.tipo !== "informativa") total += m.peso * dieta.deficit[k]; });
      for (const m of sinOfertaReal(dieta, sinAptos[i])) total += m.peso;
    });
    return total;
  }

  function faltantes(sol, sinAptos, nombres) {
    const salida = [];
    sol.dietas.forEach((dieta, i) => {
      const prefijo = nombres.length > 1 ? `${nombres[i]}: ` : "";
      dieta.metas.forEach((m, k) => {
        if (m.tipo !== "energia" && m.tipo !== "informativa" && dieta.deficit[k] > 0.005) salida.push(prefijo + m.nombre);
      });
      for (const m of sinOfertaReal(dieta, sinAptos[i])) salida.push(`${prefijo}${m.nombre} (no lo vende)`);
    });
    return salida;
  }

  function cobertura(dieta, req, sinAptos) {
    const nutrientes = [], reglasCob = [];
    const porClave = new Map(dieta.metas.map((m, k) => [m.clave, [m, dieta.valores[k], dieta.deficit[k]]]));
    const periodo = (fila, m) => {
      const f = m.semanal ? 7 : 1;
      for (const c of ["valor", "minimo", "maximo"]) if (fila[c] !== null) fila[c] = redondear(fila[c] * f, 2);
      fila.unidad = m.tipo === "regla" ? `${m.unidad} por ${m.semanal ? "semana" : "día"}` : m.unidad;
      return fila;
    };
    for (const m0 of req.metas) {
      if (!porClave.has(m0.clave)) {
        const noAplica = sinAptos.has(m0.clave);
        reglasCob.push(periodo({ clave: m0.clave, nombre: m0.nombre, unidad: m0.unidad, valor: noAplica ? null : 0,
          minimo: m0.minimo, maximo: m0.maximo, estado: noAplica ? "no_aplica" : "falta",
          nota: noAplica ? "no aplica: ningún alimento apto cuenta para esta regla"
            : "la sucursal no vende ningún alimento apto que cuente para esta regla",
          fuente: m0.fuente, tipo: m0.tipo, porcentaje: noAplica ? null : 0 }, m0));
        continue;
      }
      const [m, v, dfc] = porClave.get(m0.clave);
      let estado;
      if (m.tipo === "informativa") estado = "informativa";
      else if (dfc <= 0.005) estado = "cumple";
      else if (m.minimo && v < m.minimo) estado = "falta";
      else estado = "excede";
      const referencia = m.minimo ? m.minimo : m.maximo;
      const fila = { clave: m.clave, nombre: m.nombre, unidad: m.unidad, valor: redondear(v, 2), minimo: m.minimo,
        maximo: m.maximo, estado, nota: m.nota, fuente: m.fuente, tipo: m.tipo,
        porcentaje: referencia ? redondear(v / referencia * 100, 1) : null };
      (m.tipo === "regla" ? reglasCob : nutrientes).push(periodo(fila, m));
    }
    return [nutrientes, reglasCob];
  }

  function grupos(oferta, consumo) {
    const pr = D.productos, suma = new Map();
    oferta.forEach((f, pos) => {
      const g = pr.grupo_alimentario[f.p];
      const s = suma.get(g) || { g: 0, kcal: 0 };
      s.g += consumo[pos];
      s.kcal += pr.energia_kcal[f.p] / 100 * consumo[pos];
      suma.set(g, s);
    });
    const filas = [...suma.entries()].filter(([, s]) => s.g > 0).sort((a, b) => comparar(a[0], b[0]));
    const total = filas.reduce((t, [, s]) => t + s.kcal, 0) || 1;
    filas.sort((a, b) => b[1].kcal - a[1].kcal);
    return filas.map(([g, s]) => ({ grupo: g, gramos_dia: Math.round(s.g), kcal_dia: Math.round(s.kcal),
      pct_kcal: redondear(s.kcal / total * 100, 1) }));
  }

  // Gramos comestibles por día que come todo el hogar de cada producto (Solucion.consumo).
  function consumoHogar(sol) {
    const consumo = new Float64Array(sol.oferta.length);
    for (const dt of sol.dietas) dt.consumo.forEach((v, pos) => { consumo[pos] += v; });
    return consumo;
  }

  // Un renglón del ticket: el producto j de la oferta, con lo que se compra y lo que come cada persona.
  function renglon(sol, j, dias, consumo) {
    const pr = D.productos, f = sol.oferta[j], x = sol.compra[j];
    const comestible = x * f.gc;
    const sobra = comestible - consumo[j] * dias;
    const agua = pr.es_agua[f.p] === 1;
    return {
      id_producto: pr.id[f.p], nombre: pr.nombre[f.p], marca: pr.marca[f.p], subcategoria: pr.subcategoria[f.p],
      grupo: pr.grupo_alimentario[f.p], cantidad: cantidad(f, x), unidades_compra: x, granel: f.granel,
      precio_unitario: redondear(f.precio, 2),
      precio_unidad_texto: f.granel ? `$${fmt(f.precio, 2)} /kg` : `$${fmt(f.precio, 2)} c/u`,
      subtotal: redondear(x * f.precioCompra, 2), promocion: Number.isNaN(f.promo) ? null : redondear(f.promo, 2),
      gramos_dia: redondear(consumo[j], 1), consumo_dia_texto: gramosTexto(consumo[j], agua), agua,
      por_persona: sol.dietas.map((dt) => redondear(dt.consumo[j], 1)),
      sobrante_texto: sobra > Math.max(20, 0.05 * comestible) ? gramosTexto(sobra, agua) : "",
      fuente_nutrientes: pr.fuente_nutrientes[f.p],
    };
  }

  // Orden del ticket: por grupo de la canasta, subcategoría y nombre.
  function ordenarItems(items) {
    const orden = new Map(P.GRUPOS_CANASTA.map((g, i) => [g, i]));
    return items.sort((a, b) => ((orden.get(a.grupo) ?? 99) - (orden.get(b.grupo) ?? 99))
      || comparar(a.subcategoria, b.subcategoria) || comparar(a.nombre, b.nombre));
  }

  // La sucursal t como la muestra el ticket (con los minutos caminando desde el lugar, si se buscó por tiempo).
  function datosTienda(t, distancia, tiempo = {}) {
    const T = D.tiendas;
    return { id: T.id[t], bandera: T.bandera[t], comercio: T.comercio[t], cuit: T.cuit[t], sucursal: T.sucursal_nombre[t],
      direccion: T.direccion[t], localidad: T.localidad[t], barrio: T.barrio[t], provincia: T.provincia[t],
      lat: T.lat[t], lon: T.lon[t], distancia_km: redondear(distancia, 2), ...caminata(tiempo), hoy: horarioHoy(t),
      tipo: T.tipo_sucursal[t] };
  }

  function ticket(sol, t, distancia, dias, tiempo = {}) {
    const pr = D.productos;
    const consumo = consumoHogar(sol);
    const items = [];
    sol.oferta.forEach((f, j) => { if (sol.compra[j] > 0) items.push(renglon(sol, j, dias, consumo)); });
    ordenarItems(items);
    const total = redondear(items.reduce((s, it) => s + it.subtotal, 0), 2);
    const energia = sol.oferta.reduce((s, f, pos) => s + pr.energia_kcal[f.p] / 100 * consumo[pos], 0);
    return {
      tienda: datosTienda(t, distancia, tiempo),
      fecha_precios: D.fecha, dias, items, total, costo_diario: redondear(total / dias, 2),
      costo_1000_kcal: energia ? redondear(total / dias / energia * 1000, 2) : null,
      promociones_disponibles: items.filter((it) => it.promocion).length,
    };
  }

  function datosPersona(p, nombre) {
    return { nombre, sexo: p.sexo, edad: p.edad, peso_kg: p.peso_kg, altura_cm: p.altura_cm,
      actividad: P.ACTIVIDAD[p.actividad].nombre, objetivo: P.OBJETIVO[p.objetivo].nombre, etapa: p.etapa,
      trimestre: p.trimestre, restricciones: p.restricciones.map((r) => P.RESTRICCIONES[r]) };
  }

  function personaDesde(dic) {
    const num = (v, entero) => (v === null || v === undefined || v === "" ? null : entero ? parseInt(v, 10) : Number(v));
    return { sexo: String(dic.sexo ?? ""), edad: num(dic.edad, true) || 0, peso_kg: num(dic.peso_kg) || 0,
      altura_cm: num(dic.altura_cm), actividad: String(dic.actividad ?? "liviana"), objetivo: String(dic.objetivo ?? "mantener"),
      etapa: String(dic.etapa ?? "general"), trimestre: num(dic.trimestre, true),
      restricciones: (dic.restricciones || []).map(String), nombre: String(dic.nombre ?? "").slice(0, 40) };
  }

  // (cumple, total) de las metas que se le exigen a la compra (resultado.metas_cubiertas).
  function metasCubiertas(persona) {
    const exigidas = persona.cobertura.concat(persona.reglas).filter((c) => c.estado !== "informativa" && c.estado !== "no_aplica");
    return [exigidas.filter((c) => c.estado === "cumple").length, exigidas.length];
  }

  // Cuántas metas logra la compra y cuáles faltan (resultado._metas, con resumen_metas).
  function metasResumen(r) {
    const cuentas = r.personas.map(metasCubiertas);
    const varias = r.personas.length > 1;
    const faltan = [];
    for (const p of r.personas) {
      for (const c of p.cobertura.concat(p.reglas)) {
        if (c.estado !== "falta" && c.estado !== "excede") continue;
        // Lo que se pasa se mide contra el máximo; lo que falta, contra el mínimo.
        const pct = (c.estado === "excede" && c.maximo ? c.valor / c.maximo * 100 : c.porcentaje) || 0;
        faltan.push({ persona: varias ? p.datos.nombre : "", clave: c.clave, nombre: c.nombre.split(":")[0],
          estado: c.estado, porcentaje: redondear(pct, 1), no_lo_vende: c.valor === 0 && c.nota.includes("no vende") });
      }
    }
    return { cumple: cuentas.reduce((s, [c]) => s + c, 0), total: cuentas.reduce((s, [, t]) => s + t, 0), faltan };
  }

  const nombresHogar = (personas) => personas.map((p, i) => p.nombre || `Persona ${i + 1}`);

  // Qué puede comer cada persona: aptos, efecto de cada restricción y reglas que no aplican (resultado._aptos_hogar).
  function aptosHogar(personas, reqs, listos, agua) {
    const pr = D.productos;
    const compraAgua = P.AGUA_MODOS[agua].compra;          // si no, el agua es la de la canilla: no se compra
    const aptosP = [], efectos = [], sinAptos = [];
    personas.forEach((p, i) => {
      const { apto, efecto } = aptos(p.restricciones, compraAgua);
      if (listos) {
        let excluye = 0;
        for (let k = 0; k < pr.n; k++) if (apto[k] && pr.a_cocinar[k]) { excluye++; apto[k] = 0; }
        efecto.push({ clave: "listos", nombre: P.LISTOS_NOMBRE, excluye });
      }
      aptosP.push(apto);
      efectos.push(efecto);
      const aptosIdx = [];
      for (let k = 0; k < pr.n; k++) if (apto[k]) aptosIdx.push(k);
      // Reglas que ningún producto apto (en todo el país) puede cumplir: no aplican por las restricciones.
      sinAptos.push(new Set(reqs[i].metas.filter((m) => m.tipo === "regla" && m.minimo !== null
        && !coeficientes(aptosIdx, m).some((v) => v !== 0)).map((m) => m.clave)));
    });
    return { aptosP, efectos, sinAptos };
  }

  // Mismos productos con los mismos precios (al centavo) = misma firma: dan la misma canasta (resultado._firma).
  const firma = (o) => o.oferta.map((f) => `${f.p}:${redondear(f.precioCompra, 2)}`).join("|");

  async function armar(pedido, avance = () => {}) {
    const inicio = Date.now();
    const personas = pedido.personas.map(personaDesde);
    const { lat, lon } = pedido;
    const dias = pedido.dias ?? P.DIAS_PREDETERMINADO;
    const listos = Boolean(pedido.listos);
    const agua = pedido.agua ?? P.AGUA_MODO_PREDETERMINADO;
    if (!(personas.length >= 1 && personas.length <= P.PERSONAS_MAXIMAS)) {
      throw new Error(`El hogar tiene que tener entre 1 y ${P.PERSONAS_MAXIMAS} personas.`);
    }
    if (!(String(dias) in P.DIAS_PERIODO)) {
      throw new Error(`El período tiene que ser de ${Object.keys(P.DIAS_PERIODO).join(", ")} días.`);
    }
    if (!(agua in P.AGUA_MODOS)) throw new Error(`El agua tiene que ser ${Object.keys(P.AGUA_MODOS).join(", ")}.`);
    const nombres = nombresHogar(personas);
    const errores = personas.map((p, i) => validar(p).map((e) => (personas.length > 1 ? `${nombres[i]}: ${e}` : e))).flat();
    if (errores.length) throw new Error(errores.join(" "));
    const reqs = personas.map((p) => calcular(p, agua));
    const pr = D.productos;
    const compraAgua = P.AGUA_MODOS[agua].compra;
    const { aptosP, efectos, sinAptos } = aptosHogar(personas, reqs, listos, agua);
    const base = {
      personas: personas.map((p, i) => ({
        datos: datosPersona(p, nombres[i]),
        requerimientos: { energia_kcal: reqs[i].energia_kcal, proteina_g_kg: reqs[i].proteina_g_kg,
          peso_referencia_kg: redondear(reqs[i].peso_referencia_kg, 1), pasos: reqs[i].pasos, avisos: reqs[i].avisos },
        restricciones: { criterios: criterios(p.restricciones), efecto: efectos[i],
          productos_aptos: aptosP[i].reduce((s, v) => s + v, 0) },
      })),
      hogar: { personas: personas.length, energia_kcal: reqs.reduce((s, r) => s + r.energia_kcal, 0) },
      opciones: { listos, listos_criterio: listos ? P.LISTOS_CRITERIO : null, agua, agua_nombre: P.AGUA_MODOS[agua].nombre },
      catalogo: { productos_total: D.productosTotal,
        productos_canasta: compraAgua ? pr.n : pr.n - pr.es_agua.reduce((s, v) => s + v, 0), excluidos_siempre: P.EXCLUIDOS_SIEMPRE },
      ubicacion: { lat, lon }, dias, periodo: P.DIAS_PERIODO[String(dias)], fecha_precios: D.fecha,
    };
    // Con tiempos caminando (de rutas.js), solo las sucursales dentro del límite; si no, las más cercanas en línea recta.
    const porTiempo = pedido.tiempos != null;
    const limite = pedido.caminata_minutos ?? P.CAMINATA_MINUTOS;
    if (porTiempo) {
      const estimado = Object.values(pedido.tiempos).some((v) => v.fuente === "estimado");
      base.caminata = { minutos: limite, aviso: pedido.aviso_tiempos ?? null, fuente: estimado ? "estimado" : "ruta" };
    }
    const cercanas = porTiempo ? sucursalesPorTiempo(lat, lon, pedido.tiempos, limite) : sucursalesCercanas(lat, lon);
    if (!cercanas.length) {
      base.error = porTiempo ? `No hay supermercados con precios en SEPA a menos de ${fmt(limite)} minutos caminando.`
        : `No hay supermercados con precios en SEPA a menos de ${fmt(P.RADIO_MAXIMO_KM)} km.`;
      base.sin_sucursales = true;
      return base;
    }
    // Ofertas; las sucursales con la misma oferta y los mismos precios se resuelven una vez.
    const ofertas = cercanas.map((x) => ofertaTienda(x.i, aptosP));
    const firmas = new Map(), unica = [];
    ofertas.forEach((o, k) => {
      const f = firma(o);
      if (!firmas.has(f)) firmas.set(f, k);
      unica.push(firmas.get(f));
    });
    const resueltas = new Map();
    const pendientes = [...new Set(unica)];
    let hechas = 0;
    avance({ hechas, total: pendientes.length, sucursal: "" });
    await Promise.all(pendientes.map(async (k) => {
      const o = ofertas[k];
      resueltas.set(k, await resolver(reqs.map((r, i) => [r, o.porPersona[i]]), o.oferta, dias));
      const t = cercanas[k].i;
      avance({ hechas: ++hechas, total: pendientes.length, sucursal: `${D.tiendas.bandera[t]} ${D.tiendas.sucursal_nombre[t]}` });
    }));
    const soluciones = unica.map((k) => resueltas.get(k));
    const T = D.tiendas;
    const comparacion = cercanas.map((x, k) => {
      const s = soluciones[k];
      const ok = s.estado !== "sin_solucion";
      return { id: T.id[x.i], bandera: T.bandera[x.i], sucursal: T.sucursal_nombre[x.i], direccion: T.direccion[x.i],
        localidad: T.localidad[x.i], distancia_km: redondear(x.d, 2), ...caminata(x), lat: T.lat[x.i], lon: T.lon[x.i],
        estado: s.estado,
        costo: ok ? redondear(s.costo, 2) : null, puntaje: ok ? redondear(puntaje(s, sinAptos), 3) : null,
        faltantes: ok ? faltantes(s, sinAptos, nombres) : [], mensaje: ok ? "" : s.mensaje,
        productos_considerados: s.oferta.length, segundos: redondear(s.segundos, 2) };
    });
    const validas = comparacion.map((c, k) => [c, k]).filter(([c]) => c.costo !== null);
    if (!validas.length) {
      base.sucursales = comparacion;
      base.error = "Ninguna sucursal cercana tiene alimentos aptos suficientes para armar la canasta.";
      return base;
    }
    const [elegida, ke] = validas.reduce((mejor, act) => {
      const a = [redondear(act[0].puntaje, 2), act[0].costo], b = [redondear(mejor[0].puntaje, 2), mejor[0].costo];
      return a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]) ? act : mejor;
    });
    elegida.elegida = true;
    const sol = soluciones[ke];
    base.personas.forEach((persona, i) => {
      [persona.cobertura, persona.reglas] = cobertura(sol.dietas[i], reqs[i], sinAptos[i]);
      persona.grupos = grupos(sol.oferta, sol.dietas[i].consumo);
    });
    const metasModelo = sol.dietas.reduce((s, dt) => s + dt.metas.length, 0);
    Object.assign(base, {
      sucursales: comparacion,
      ticket: ticket(sol, cercanas[ke].i, cercanas[ke].d, dias, cercanas[ke]),
      modelo: { estado: sol.estado, productos_considerados: sol.oferta.length,
        variables: sol.oferta.length * (1 + personas.length) + metasModelo, metas: metasModelo,
        segundos_sucursal: redondear(sol.segundos, 2), segundos_total: redondear((Date.now() - inicio) / 1000, 2),
        gap: P.GAP_RELATIVO },
    });
    return base;
  }

  // ============================================================
  // Compra en dos supermercados (resultado.dos_super)
  // ============================================================

  // Las ofertas de A y de B en una sola; cada fila lleva su sucursal (tienda). Una fila de B con el mismo producto que
  // A vende al mismo precio o más barato se saca: nunca puede ser mejor y haría el modelo más lento.
  function union(oa, ob, ta, tb) {
    const precioA = new Map(oa.oferta.map((f) => [f.p, f.precioCompra]));
    const queda = ob.oferta.map((f) => !precioA.has(f.p) || f.precioCompra < precioA.get(f.p));
    const oferta = oa.oferta.map((f) => ({ ...f, tienda: ta }))
      .concat(ob.oferta.filter((_, k) => queda[k]).map((f) => ({ ...f, tienda: tb })));
    return { oferta, porPersona: oa.porPersona.map((a, i) => a.concat(ob.porPersona[i].filter((_, k) => queda[k]))) };
  }

  // La compra más barata que mejor cubre las metas comprando en A y en B (el modelo de siempre sobre la unión).
  function par(reqs, oa, ob, ta, tb, dias) {
    const o = union(oa, ob, ta, tb);
    return resolver(reqs.map((r, i) => [r, o.porPersona[i]]), o.oferta, dias);
  }

  const compraEn = (sol, t) => sol.estado !== "sin_solucion" && sol.oferta.some((f, j) => sol.compra[j] > 0 && f.tienda === t);

  // Lo mínimo que tiene que ahorrar la compra en dos sucursales (con las mismas metas) para proponerla.
  const ahorroMinimo = (costoA) => redondear(Math.max(costoA * P.DOS_SUPER_AHORRO_MINIMO_PCT / 100,
    P.DOS_SUPER_AHORRO_MINIMO_PESOS), 2);

  // [estado, motivo, mejor par] (resultado._decidir): el mejor par es el de menor déficit (al 1 %) y, a igual déficit,
  // el más barato, entre los que compran algo en B.
  function decidir(costoA, puntajeA, vecinas) {
    if (!vecinas.length) return ["sin_vecinas", null, null];
    const conB = vecinas.filter((v) => v.compra_en_b);
    if (!conB.length) return ["no_conviene", null, null];
    const clave = (v) => [redondear(v.puntaje, 2), v.costo];
    const mejor = conB.reduce((m, v) => {
      const [pv, cv] = clave(v), [pm, cm] = clave(m);
      return pv < pm || (pv === pm && cv < cm) ? v : m;
    });
    const pA = redondear(puntajeA, 2), pB = redondear(mejor.puntaje, 2);
    if (pB < pA) return ["conviene", "metas", mejor];
    if (pB === pA && redondear(costoA - mejor.costo, 2) >= ahorroMinimo(costoA)) return ["conviene", "ahorro", mejor];
    return ["no_conviene", null, mejor];
  }

  // Minutos caminando del lugar a la sucursal: los del resultado (ruta o estimado) o, si no se buscó por tiempo,
  // estimados con la distancia en línea recta.
  const minutosCasa = (x) => (x.minutos !== undefined && x.minutos !== null && !Number.isNaN(x.minutos)
    ? [redondear(x.minutos, 1), x.fuente || "ruta"] : [redondear(minutosEstimados(x.d), 1), "estimado"]);

  // Circuito lugar → A → B → lugar contra la ida y vuelta a A, con los tramos redondeados a 0,1 min (A → B, estimado).
  function circuito(a, b) {
    const [casaA, fuenteA] = minutosCasa(a);
    const [casaB, fuenteB] = minutosCasa(b);
    const aB = redondear(b.minutosDesdeA, 1);
    const total = redondear(casaA + aB + casaB, 1);
    const soloA = redondear(2 * casaA, 1);
    return { solo_a: soloA, circuito: total, extra: redondear(Math.max(0, total - soloA), 1), fuente: "estimado",
      tramos: [{ desde: "lugar", hasta: "a", minutos: casaA, fuente: fuenteA },
        { desde: "a", hasta: "b", minutos: aB, fuente: "estimado", metros_linea_recta: Math.round(b.kmDesdeA * 1000) },
        { desde: "b", hasta: "lugar", minutos: casaB, fuente: fuenteB }] };
  }

  // El ticket de la compra combinada, un bloque por sucursal (A primero) con su subtotal; cada renglón dice de qué
  // sucursal es (id_tienda).
  function ticketDividido(sol, sucursales, dias, fecha) {
    const consumo = consumoHogar(sol);
    const bloques = sucursales.map((x) => {
      const items = [];
      sol.oferta.forEach((f, j) => {
        if (sol.compra[j] > 0 && f.tienda === x.i) items.push({ ...renglon(sol, j, dias, consumo), id_tienda: D.tiendas.id[x.i] });
      });
      ordenarItems(items);
      return { tienda: datosTienda(x.i, x.d, x), items, subtotal: redondear(items.reduce((s, it) => s + it.subtotal, 0), 2) };
    });
    const total = redondear(bloques.reduce((s, b) => s + b.subtotal, 0), 2);
    return { fecha_precios: fecha, dias, sucursales: bloques, total, costo_diario: redondear(total / dias, 2) };
  }

  // Los nombres separados por punto y coma: a lo sumo n, y cuántos más.
  const lista = (xs, n = 4) => xs.slice(0, n).join("; ") + (xs.length > n ? ` (y ${xs.length - n} más)` : "");

  function mensajeDosSuper(motivo, nombreA, nombreB, productosB, ahorro, pct, minimo, extra, antes, despues) {
    const cuales = lista(productosB.map(minusc));
    const caminando = extra >= 1 ? `caminando unos ${fmt(extra, 1)} min más (estimado)` : "casi sin caminar de más (estimado)";
    if (motivo === "metas") {
      const logro = despues.cumple > antes.cumple
        ? `llegás a ${despues.cumple} de ${despues.total} metas (con ${nombreA} sola, ${antes.cumple})`
        : `cubrís mejor las que faltan (${despues.cumple} de ${despues.total} metas, como antes)`;
      const plata = ahorro > 0 ? `ahorrás $${fmt(ahorro)}` : ahorro < 0 ? `cuesta $${fmt(-ahorro)} más` : "cuesta lo mismo";
      return `Con un segundo súper ${logro}: en ${nombreB} conviene comprar ${cuales}. ` +
        `${plata[0].toUpperCase() + plata.slice(1)}, ${caminando}.`;
    }
    if (motivo === "ahorro") return `Comprando en ${nombreB} ${cuales} ahorrás $${fmt(ahorro)} (${fmt(pct, 1)} %), ${caminando}.`;
    if (ahorro >= minimo) {   // ahorraría lo suficiente, pero no se elige porque cubre peor las metas
      return `No conviene dividir la compra: comprando en ${nombreB} ${cuales} ahorrarías $${fmt(ahorro)}, pero ` +
        `cubrirías peor las metas (${despues.cumple} de ${despues.total}; con ${nombreA} sola, ${antes.cumple}).`;
    }
    if (ahorro > 0) {
      return `No conviene dividir la compra: comprando en ${nombreB} ${cuales} ahorrarías solo $${fmt(ahorro)} ` +
        `(${fmt(pct, 1)} %), menos del mínimo de $${fmt(minimo)}.`;
    }
    return `No conviene dividir la compra: sumando ${nombreB} no sale más barato ni cubre mejor las metas.`;
  }

  // ¿Conviene comprar en dos supermercados? Espejo de resultado.dos_super (ver su docstring: el modelo con binarias de
  // visita se resuelve enumerando los pares (A, B), cada uno con el modelo de siempre). Se calcula a pedido, después
  // del resultado r de armar (no lo cambia). pedido: el mismo que se le pasó a armar (se usan personas y tiempos); el
  // lugar, los días, "listos" y el agua salen de r.
  async function dosSuper(pedido, r, avance = () => {}) {
    const inicio = Date.now();
    if (!r || !r.ticket) throw new Error("Primero hay que armar la canasta: el resultado no tiene una compra.");
    if (P.DOS_SUPER_MAXIMO !== 2) {
      throw new Error("La compra en varias sucursales se resuelve por pares: DOS_SUPER_MAXIMO tiene que ser 2.");
    }
    const porTiempo = r.caminata != null;
    const tiempos = pedido.tiempos ?? null;
    if (porTiempo && tiempos === null) throw new Error("El resultado se armó por tiempo caminando: hacen falta los mismos tiempos.");
    const { lat, lon } = r.ubicacion;
    const dias = r.dias, listos = r.opciones.listos, agua = r.opciones.agua;
    const personas = pedido.personas.map(personaDesde);
    const nombres = nombresHogar(personas);
    const reqs = personas.map((p) => calcular(p, agua));
    const { aptosP, sinAptos } = aptosHogar(personas, reqs, listos, agua);
    const T = D.tiendas;

    // Sucursales que pueden ser B: las alcanzables dentro del límite (por tiempo) o las evaluadas.
    const elegida = r.sucursales.find((s) => s.elegida);
    const pool = porTiempo ? sucursalesPorTiempo(lat, lon, tiempos, r.caminata.minutos, Object.keys(tiempos).length)
      : sucursalesPorId(lat, lon, r.sucursales.map((s) => s.id));
    const a = pool.find((x) => T.id[x.i] === elegida.id);
    if (!a) throw new Error("La sucursal elegida no está entre las alcanzables: ¿son los mismos tiempos?");
    const cercanas = vecinasDe(pool, a, P.DOS_SUPER_MINUTOS_ENTRE);
    // Las que venden lo mismo al mismo precio que A (o que otra más cercana) no suman nada.
    const ofertas = new Map([[a.i, ofertaTienda(a.i, aptosP)]]);
    const vistas = new Set([firma(ofertas.get(a.i))]), distintas = [];
    for (const x of cercanas) {
      const o = ofertaTienda(x.i, aptosP);
      ofertas.set(x.i, o);
      const f = firma(o);
      if (!vistas.has(f)) { vistas.add(f); distintas.push(x); }
    }
    const vecinas = elegirVecinas(distintas, T.bandera[a.i], P.DOS_SUPER_VECINAS);

    // Con el grupo de workers de solver (dentro de un worker), los pares se resuelven en paralelo, como en armar.
    let hechas = 0;
    avance({ hechas, total: vecinas.length, sucursal: "" });
    const soluciones = await Promise.all(vecinas.map(async (x) => {
      const s = await par(reqs, ofertas.get(a.i), ofertas.get(x.i), a.i, x.i, dias);
      avance({ hechas: ++hechas, total: vecinas.length, sucursal: `${T.bandera[x.i]} ${T.sucursal_nombre[x.i]}` });
      return s;
    }));
    const probadas = vecinas.map((x, k) => {
      const s = soluciones[k];
      const ok = s.estado !== "sin_solucion";
      return { id: T.id[x.i], bandera: T.bandera[x.i], sucursal: T.sucursal_nombre[x.i], direccion: T.direccion[x.i],
        lat: T.lat[x.i], lon: T.lon[x.i], minutos_desde_a: redondear(x.minutosDesdeA, 1), estado: s.estado,
        costo: ok ? redondear(s.costo, 2) : null, puntaje: ok ? redondear(puntaje(s, sinAptos), 3) : null,
        compra_en_b: compraEn(s, x.i), segundos: redondear(s.segundos, 2) };
    });

    const costoA = elegida.costo, puntajeA = elegida.puntaje;
    const [estado, motivo, mejor] = decidir(costoA, puntajeA, probadas);
    const nombreA = `${T.bandera[a.i]} ${T.sucursal_nombre[a.i]}`;
    const salida = { estado, motivo, mensaje: "", maximo_sucursales: P.DOS_SUPER_MAXIMO,
      minutos_entre_max: P.DOS_SUPER_MINUTOS_ENTRE, a: datosTienda(a.i, a.d, a), b: null,
      costo_a: costoA, costo_combinado: null, ahorro: null, ahorro_pct: null,
      ahorro_minimo: ahorroMinimo(costoA), puntaje_a: puntajeA, puntaje_combinado: null,
      metas_antes: metasResumen(r), metas_despues: null, minutos: null, ticket: null, productos_b: [],
      personas: null, vecinas: probadas };
    if (mejor === null) {
      if (estado === "sin_vecinas") {
        const donde = porTiempo ? "dentro de tu límite de caminata" : "entre las evaluadas";
        salida.mensaje = `No hay otro supermercado con otros precios a menos de ${P.DOS_SUPER_MINUTOS_ENTRE} min ` +
          `caminando de ${nombreA} (${donde}): la compra queda en uno solo.`;
      } else {
        const cuantas = probadas.length === 1 ? "la vecina probada" : `las ${probadas.length} vecinas probadas`;
        salida.mensaje = `No conviene dividir la compra: con ${cuantas}, lo mejor sigue siendo comprar todo en ${nombreA}.`;
      }
      salida.segundos = redondear((Date.now() - inicio) / 1000, 2);
      return salida;
    }

    const k = probadas.indexOf(mejor);
    const sol = soluciones[k], b = vecinas[k];
    const ahorro = redondear(costoA - mejor.costo, 2);
    const pct = redondear(ahorro / costoA * 100, 1);
    const tk = ticketDividido(sol, [a, b], dias, r.fecha_precios);
    const productosB = [...new Set(tk.sucursales[1].items.map((it) => it.subcategoria))];
    const personasC = sol.dietas.map((dieta, i) => {
      const [cob, reg] = cobertura(dieta, reqs[i], sinAptos[i]);
      return { datos: { nombre: nombres[i] }, cobertura: cob, reglas: reg, grupos: grupos(sol.oferta, dieta.consumo) };
    });
    const metasC = metasResumen({ personas: personasC });
    const minutos = circuito(a, b);
    Object.assign(salida, {
      mensaje: mensajeDosSuper(motivo, nombreA, `${T.bandera[b.i]} ${T.sucursal_nombre[b.i]}`, productosB, ahorro, pct,
        salida.ahorro_minimo, minutos.extra, salida.metas_antes, metasC),
      b: { ...datosTienda(b.i, b.d, b), minutos_desde_a: minutos.tramos[1].minutos, km_desde_a: redondear(b.kmDesdeA, 2) },
      costo_combinado: mejor.costo, ahorro, ahorro_pct: pct, puntaje_combinado: mejor.puntaje, metas_despues: metasC,
      minutos, ticket: tk, productos_b: productosB, personas: motivo === "metas" ? personasC : null,
      segundos: redondear((Date.now() - inicio) / 1000, 2),
    });
    return salida;
  }

  // ============================================================
  // Interfaz con la página
  // ============================================================

  const Motor = { cargarPaquete, cargarDatos, armar, dosSuper, calcular, personaDesde, validar, candidatasCaminando,
    precargarSolver: () => grupoDeSolvers() };

  if (EN_WORKER) {
    self.onmessage = async (e) => {
      const { tipo, id } = e.data;
      try {
        if (tipo === "paquete") {
          const resumen = await cargarPaquete(e.data.meta, e.data.binario);
          self.postMessage({ tipo: "listo", id, resumen });
          grupoDeSolvers().catch(() => {});        // se prepara el solver mientras la persona completa los datos
        } else if (tipo === "candidatas") {
          self.postMessage({ tipo: "resultado", id, candidatas: candidatasCaminando(e.data.lat, e.data.lon, e.data.minutos) });
        } else if (tipo === "armar") {
          const r = await armar(e.data.pedido, (a) => self.postMessage({ tipo: "avance", id, ...a }));
          self.postMessage({ tipo: "resultado", id, resultado: r });
        } else if (tipo === "dos_super") {
          // pedido: el mismo de "armar"; resultado: lo que devolvió "armar" con ese pedido.
          const ds = await dosSuper(e.data.pedido, e.data.resultado, (a) => self.postMessage({ tipo: "avance", id, ...a }));
          self.postMessage({ tipo: "resultado", id, dos_super: ds });
        }
      } catch (err) {
        self.postMessage({ tipo: "error", id, mensaje: err && err.message ? err.message : String(err) });
      }
    };
  } else {
    window.MotorCanasta = Motor;
  }
})();
