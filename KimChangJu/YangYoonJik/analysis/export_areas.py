from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd

from analysis.pipeline import ROOT


def load_songpa_areas() -> gpd.GeoDataFrame:
    archive_path = ROOT / "data/raw/area/areas.zip"
    if not archive_path.exists():
        return gpd.GeoDataFrame()
    with TemporaryDirectory() as directory:
        target = Path(directory)
        with zipfile.ZipFile(archive_path) as archive:
            for index, info in enumerate(archive.infolist()):
                suffix = Path(info.filename).suffix.lower()
                if suffix in {".shp", ".shx", ".dbf", ".prj", ".cpg"}:
                    (target / f"areas{suffix}").write_bytes(archive.read(info))
        areas = gpd.read_file(target / "areas.shp")
    areas = areas.rename(columns={"TRDAR_CD": "areaId", "TRDAR_CD_N": "areaName", "SIGNGU_CD_": "districtName", "ADSTRD_CD_": "dongName"})
    areas["areaId"] = areas["areaId"].astype(str)
    return areas[areas["districtName"] == "송파구"].to_crs(4326).copy()


def main() -> int:
    areas = load_songpa_areas()
    target = ROOT / "public/data/areas.geojson"
    if areas.empty:
        target.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
        print("송파구 영역 원본 없음")
        return 2
    areas[["areaId", "areaName", "dongName", "geometry"]].to_file(target, driver="GeoJSON")
    print(f"{len(areas)} Songpa features exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
