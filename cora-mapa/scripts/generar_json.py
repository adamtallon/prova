"""
Genera docs/datos_mapa.json con las ubicaciones de los datasets publicados
de una colección de CORA.RDR (Dataverse, CSUC).

- Solo hace peticiones de lectura (GET) y NO necesita token: ve únicamente
  los datasets publicados, que es lo que debe aparecer en un mapa público.
- Ubicaciones: coordenadas (bounding box), coordenadas escritas en texto libre
  y ciudades (tabla propia + geocodificación de respaldo con Nominatim).
- Lo que no se puede situar queda en docs/pendientes.json para revisarlo.

Uso:  python scripts/generar_json.py
"""
import datetime
import json
import re
import time
import unicodedata
from pathlib import Path

import requests

# ---------- CONFIGURACIÓN ----------
BASE_URL = "https://dataverse.csuc.cat"
COLECCION = "upc"
PAUSA = 0.2                      # segundos entre peticiones a CORA
USAR_NOMINATIM = True            # geocodificar ciudades que no estén en la tabla
# ------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "datos_mapa.json"
PENDIENTES = RAIZ / "docs" / "pendientes.json"
CACHE = RAIZ / "scripts" / "geocache.json"
UA = "cora-upc-mapa/1.0 (biblioteca UPC; datos abiertos)"


def norm(s):
    """Minúsculas, sin acentos y con espacios normalizados."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


# Tabla de ciudades: nombre normalizado -> (latitud, longitud, país)
CIUDADES = {
    "barcelona": (41.3874, 2.1686, "Spain"),
    "barcelonaa": (41.3874, 2.1686, "Spain"),          # errata frecuente
    "terrassa": (41.5633, 2.0083, "Spain"),
    "castelldefels": (41.2800, 1.9753, "Spain"),
    "lleida": (41.6176, 0.6200, "Spain"),
    "manresa": (41.7289, 1.8260, "Spain"),
    "sant cugat": (41.4722, 2.0864, "Spain"),
    "sant cugat del valles": (41.4722, 2.0864, "Spain"),
    "cerdanyola del valles": (41.4914, 2.1405, "Spain"),
    "sant vicenc dels horts": (41.3925, 2.0083, "Spain"),
    "sant joan despi": (41.3683, 2.0603, "Spain"),
    "madrid": (40.4168, -3.7038, "Spain"),
    "malaga": (36.7213, -4.4214, "Spain"),
    "a coruna": (43.3623, -8.4115, "Spain"),
    "paterna": (39.5033, -0.4400, "Spain"),
    "belgrade": (44.7866, 20.4489, "Serbia"),
    "belgrado": (44.7866, 20.4489, "Serbia"),
    "beograd": (44.7866, 20.4489, "Serbia"),
    "berlin": (52.5200, 13.4050, "Germany"),
    "boras": (57.7210, 12.9401, "Sweden"),
    "sortland": (68.6933, 15.4167, "Norway"),
    "narvik": (68.4385, 17.4272, "Norway"),
    "panama": (8.9824, -79.5199, "Panama"),
    "san juan del rio": (20.3883, -99.9958, "Mexico"),
}

# Tabla de ciudades ya geocodificadas por Nominatim en ejecuciones anteriores
def cargar_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def guardar_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True),
                     encoding="utf-8")


def es_espana(pais):
    return norm(pais) in {"spain", "espana", "es"}


def valor(d, clave):
    v = d.get(clave, {})
    return (v.get("value", "") if isinstance(v, dict) else "").strip()


def geocodificar(ciudad, pais, cache):
    """Devuelve (lat, lon, país) o None si no se puede situar."""
    k = norm(ciudad)
    if k in CIUDADES:
        return CIUDADES[k]
    ck = f"{k}|{norm(pais)}"
    if ck in cache:
        return tuple(cache[ck])
    if not USAR_NOMINATIM:
        return None
    try:
        q = f"{ciudad}, {pais}" if pais else ciudad
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": q, "format": "json", "limit": 1,
                                 "addressdetails": 1},
                         headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        res = r.json()
        time.sleep(1.1)                       # política de uso: máx. 1 petición/s
        if res:
            pais_res = res[0].get("address", {}).get("country", pais or "")
            out = (float(res[0]["lat"]), float(res[0]["lon"]), pais_res)
            cache[ck] = list(out)
            return out
    except Exception as e:
        print(f"  Nominatim falló para '{ciudad}': {e}")
    return None


def a_float(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def extraer_ubicaciones(version, cache, pendientes):
    """Devuelve la lista de ubicaciones de un dataset (versión más reciente)."""
    campos = version.get("metadataBlocks", {}).get("geospatial", {}).get("fields", [])
    cajas, puntos_texto, ciudades = [], [], []

    for c in campos:
        if c["typeName"] == "geographicBoundingBox":
            for b in c["value"]:
                w, e = a_float(valor(b, "westLongitude")), a_float(valor(b, "eastLongitude"))
                n, s = a_float(valor(b, "northLatitude")), a_float(valor(b, "southLatitude"))
                if None in (w, e, n, s):
                    continue
                if not (-90 <= n <= 90 and -90 <= s <= 90 and -180 <= w <= 180 and -180 <= e <= 180):
                    continue
                cajas.append((w, e, n, s))
        elif c["typeName"] == "geographicCoverage":
            for g in c["value"]:
                pais, ciudad = valor(g, "country"), valor(g, "city")
                otra = valor(g, "otherGeographicCoverage")
                if ciudad:
                    ciudades.append((ciudad, pais))
                m = re.search(r"(-?\d{1,2}\.\d+)[\s,;]+(-?\d{1,3}\.\d+)", otra)
                if m:
                    lat, lon = float(m.group(1)), float(m.group(2))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        puntos_texto.append((lat, lon, pais))

    ubic = []

    def cerca(lat, lon):
        return any(abs(u["lat"] - lat) < 0.15 and abs(u["lon"] - lon) < 0.15 for u in ubic)

    # 1) Coordenadas (lo más preciso)
    for w, e, n, s in cajas:
        lat, lon = (n + s) / 2, (w + e) / 2
        es_punto = abs(w - e) < 1e-5 and abs(n - s) < 1e-5
        if cerca(lat, lon) and any(u["lat"] == lat and u["lon"] == lon for u in ubic):
            continue
        ubic.append({"lat": round(lat, 6), "lon": round(lon, 6),
                     "tipo": "punto" if es_punto else "area",
                     "bbox": None if es_punto else [round(s, 6), round(w, 6), round(n, 6), round(e, 6)],
                     "lugar": "", "pais": ""})
    # 2) Coordenadas escritas como texto
    for lat, lon, pais in puntos_texto:
        if not cerca(lat, lon):
            ubic.append({"lat": lat, "lon": lon, "tipo": "punto", "bbox": None,
                         "lugar": "", "pais": pais})
    # 3) Ciudades (solo si no hay ya algo a menos de ~15 km)
    for ciudad, pais in ciudades:
        res = geocodificar(ciudad, pais, cache)
        if not res:
            pendientes.add((ciudad, pais))
            continue
        lat, lon, pais_res = res
        if cerca(lat, lon):
            continue
        ubic.append({"lat": lat, "lon": lon, "tipo": "ciudad", "bbox": None,
                     "lugar": ciudad, "pais": pais or pais_res})
    return ubic


def clasificar_internacional(u):
    """True si la ubicación está fuera de España."""
    if u["pais"]:
        return not es_espana(u["pais"])
    lat, lon = u["lat"], u["lon"]
    peninsula = 35.8 <= lat <= 43.9 and -9.6 <= lon <= 4.5
    canarias = 27.5 <= lat <= 29.5 and -18.5 <= lon <= -13.0
    return not (peninsula or canarias)


def listar_datasets():
    resultados, inicio, por_pagina = [], 0, 100
    while True:
        r = requests.get(f"{BASE_URL}/api/search",
                         params={"q": "*", "type": "dataset", "subtree": COLECCION,
                                 "start": inicio, "per_page": por_pagina},
                         timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        resultados += data["items"]
        inicio += por_pagina
        if inicio >= data["total_count"]:
            break
        time.sleep(PAUSA)
    return resultados


def main():
    items = listar_datasets()
    print(f"{len(items)} datasets publicados en '{COLECCION}'")
    cache, pendientes = cargar_cache(), set()
    ubicaciones, con_ubic, no_leidos = [], set(), 0

    for i, item in enumerate(items, 1):
        pid = item["global_id"]
        try:
            r = requests.get(f"{BASE_URL}/api/datasets/:persistentId/",
                             params={"persistentId": pid}, timeout=60)
            r.raise_for_status()
            version = r.json()["data"]["latestVersion"]
        except Exception:
            no_leidos += 1          # p. ej. registros recolectados de otro repositorio
            continue
        if version.get("versionState") != "RELEASED":
            continue
        ubic = extraer_ubicaciones(version, cache, pendientes)
        anio = str(item.get("published_at", ""))[:4]
        for u in ubic:
            u.update({"doi": pid, "titulo": item.get("name", ""),
                      "url": item.get("url", ""), "anio": anio,
                      "internacional": clasificar_internacional(u)})
            ubicaciones.append(u)
        if ubic:
            con_ubic.add(pid)
        if i % 25 == 0:
            print(f"  {i}/{len(items)}")
        time.sleep(PAUSA)

    guardar_cache(cache)
    salida = {
        "generado": datetime.date.today().isoformat(),
        "coleccion": COLECCION,
        "total_publicados": len(items),
        "no_leidos": no_leidos,
        "con_ubicacion": len(con_ubic),
        "ubicaciones": ubicaciones,
    }
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    PENDIENTES.write_text(json.dumps(sorted(f"{c} ({p})" if p else c for c, p in pendientes),
                                     ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo: {len(con_ubic)} datasets con ubicación, {len(ubicaciones)} puntos, "
          f"{len(pendientes)} ciudades pendientes, {no_leidos} no leídos.")


if __name__ == "__main__":
    main()
