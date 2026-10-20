"""
Bulk download of Copernicus Marine products
- Benjamin Viola, Monash University, Australia

Connect to cmems via:
conda create -n cmems -c conda-forge python=3.12 copernicusmarine
conda activate cmems
copernicusmarine login                                 #you will only need to do this once

Run from the Anaconda Prompt, with the cmems environment active:
    python download_cmems.py --dry-run                 #check IDs/variables, estimate sizes; downloads nothing
    python download_cmems.py                           #download the default products (all except wind)
    python download_cmems.py --products wind           #download only the products named
    python download_cmems.py --products ssh sic siedge

Daily and hourly products are downloaded one month per file; files that already exist are skipped,
so an interrupted run can simply be restarted. Each file is written under a temporary name and
renamed only once complete, so a half-finished download is never mistaken for a finished one.
"""

import argparse
import csv
import os
from datetime import date, timedelta

import copernicusmarine

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
OUT_DIR = r"~/Enviro layers"

#Set lat lon bounds
BBOX = dict(minimum_longitude=-180, maximum_longitude=180,
            minimum_latitude=-80, maximum_latitude=-15)

#Set date range
T0 = date(2025, 7, 1)
T1 = date(2026, 9, 30)

#One entry per dataset. depth = (min, max) in metres for 3D products, None for 2D.
#chunk = "month" (one file per month) or "all" (one file for the whole window).
REQUESTS = [
    dict(short="sst",    dataset="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
         variables=["analysed_sst", "analysis_error", "sea_ice_fraction"], depth=None, chunk="month"),
    dict(short="glorys", dataset="cmems_mod_glo_phy_my_0.083deg_P1D-m",
         variables=["thetao", "so", "mlotst", "zos"], depth=(0, 1), chunk="month"),
    dict(short="chl",    dataset="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
         variables=["CHL", "CHL_uncertainty"], depth=None, chunk="month"),
    dict(short="pft",    dataset="cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1M",
         variables=["CHL", "DIATO", "DINO", "GREEN", "HAPTO", "MICRO", "NANO", "PICO", "PROCHLO", "PROKAR"],
         depth=None, chunk="all"),
    dict(short="zoo",    dataset="cmems_mod_glo_bgc-plankton_anfc_0.25deg_P1D-m",
         variables=["zooc"], depth=(0, 1), chunk="month"),
    dict(short="wind",   dataset="cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H",
         variables=["eastward_wind", "northward_wind"], depth=None, chunk="month"),
    dict(short="ssh",    dataset="cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D",
         variables=["adt", "sla", "ugos", "vgos", "ugosa", "vgosa"], depth=None, chunk="month"),
    dict(short="sic",    dataset="osisaf_obs-si_glo_phy-sic-south_nrt_amsr2_l4_P1D-m",
         variables=["ice_conc"], depth=None, chunk="month"),
    dict(short="siedge", dataset="osisaf_obs-si_glo_phy-siedge_nrt_sh-P1D",
         variables=["ice_edge"], depth=None, chunk="month"),
]

DEFAULT_PRODUCTS = [r["short"] for r in REQUESTS if r["short"] != "wind"]  #wind: decide after the dry run as file size is huge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def month_chunks(t0, t1):
    """(start, end) date pairs, one per calendar month, clipped to [t0, t1]."""
    chunks, start = [], t0
    while start <= t1:
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        chunks.append((start, min(next_month - timedelta(days=1), t1)))
        start = next_month
    return chunks


def chunks_for(req):
    return [(T0, T1)] if req["chunk"] == "all" else month_chunks(T0, T1)


def filename_for(req, start):
    if req["chunk"] == "all":
        return f"{req['short']}_{T0:%Y%m}-{T1:%Y%m}.nc"
    return f"{req['short']}_{start:%Y%m}.nc"


def subset(req, start, end, filename, dry_run=False):
    kwargs = dict(dataset_id=req["dataset"],
                  variables=req["variables"],
                  start_datetime=f"{start:%Y-%m-%d}",
                  end_datetime=f"{end:%Y-%m-%d}T23:59:59",
                  output_directory=OUT_DIR,
                  output_filename=filename,
                  netcdf_compression_level=1,
                  dry_run=dry_run,
                  **BBOX)
    if req["depth"] is not None:
        kwargs.update(minimum_depth=req["depth"][0], maximum_depth=req["depth"][1])
    return copernicusmarine.subset(**kwargs)


# ---------------------------------------------------------------------------
# Dry run: one chunk per dataset
# ---------------------------------------------------------------------------
def dry_run(products):
    rows = []
    for req in [r for r in REQUESTS if r["short"] in products]:
        start, end = chunks_for(req)[0]
        n_files = len(chunks_for(req))
        try:
            res = subset(req, start, end, "dryrun.nc", dry_run=True)
            mb = float(res.file_size)
            rows.append(dict(short=req["short"], ok=True, mb_per_file=round(mb),
                             n_files=n_files, est_total_gb=round(mb * n_files / 1024, 1), error=""))
        except Exception as e:  #wrong ID or variable name, outside the dataset's time range, etc.
            rows.append(dict(short=req["short"], ok=False, mb_per_file="", n_files=n_files,
                             est_total_gb="", error=str(e)[:300]))

    print(f"\n{'product':<8} {'ok':<6} {'MB/file':>9} {'files':>6} {'total GB':>9}  error")
    for r in rows:
        print(f"{r['short']:<8} {str(r['ok']):<6} {str(r['mb_per_file']):>9} {r['n_files']:>6} "
              f"{str(r['est_total_gb']):>9}  {r['error'][:80]}")
    ok_gb = sum(r["est_total_gb"] for r in rows if r["ok"])
    print(f"\nEstimated total for these products: {ok_gb:.1f} GB (estimates can be off for compressed NetCDF)")

    out = os.path.join(OUT_DIR, "cmems_dry_run.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
def download(products):
    #Remove temporary files left by an interrupted run
    for f in os.listdir(OUT_DIR):
        if f.startswith("tmp_") and f.endswith(".nc"):
            os.remove(os.path.join(OUT_DIR, f))

    log_path = os.path.join(OUT_DIR, "cmems_download_log.csv")
    new_log = not os.path.exists(log_path)
    with open(log_path, "a", newline="") as log_f:
        log = csv.writer(log_f)
        if new_log:
            log.writerow(["file", "dataset", "start", "end", "result"])

        for req in [r for r in REQUESTS if r["short"] in products]:
            for start, end in chunks_for(req):
                fname = filename_for(req, start)
                final = os.path.join(OUT_DIR, fname)
                if os.path.exists(final):
                    continue
                print(f"Downloading {fname} ...", flush=True)
                tmp = "tmp_" + fname
                try:
                    subset(req, start, end, tmp)
                    os.replace(os.path.join(OUT_DIR, tmp), final)
                    result = "ok"
                except Exception as e:
                    result = "FAILED: " + str(e)[:300]
                    print("  " + result, flush=True)
                log.writerow([fname, req["dataset"], start, end, result])
                log_f.flush()

    print(f"\nDone. Log: {log_path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    major = int(copernicusmarine.__version__.split(".")[0])
    if major < 2:
        raise SystemExit(f"copernicusmarine {copernicusmarine.__version__} found; version 2 or later is needed "
                         "(conda update -c conda-forge copernicusmarine)")

    p = argparse.ArgumentParser(description="Bulk download of Copernicus Marine products")
    p.add_argument("--dry-run", action="store_true", help="estimate sizes and check requests; download nothing")
    p.add_argument("--products", nargs="+", default=None,
                   choices=[r["short"] for r in REQUESTS], help="products to process")
    args = p.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    if args.dry_run:
        dry_run(args.products or [r["short"] for r in REQUESTS])  #dry run covers everything, wind included
    else:
        download(args.products or DEFAULT_PRODUCTS)
