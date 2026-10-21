# Copernicus Bulk Files

A Python script for bulk-downloading NetCDF (`.nc`) files from the [Copernicus Marine Service](https://marine.copernicus.eu/), subset to a chosen region, date range and depth. It uses the official `copernicusmarine` toolbox.

## Features

- Downloads several ocean and sea-ice products in one run
- Splits daily and hourly products into one file per month
- Skips files that already exist, so an interrupted run can simply be restarted
- Writes each file under a temporary name and renames it only when complete, so a half-finished download is never mistaken for a finished one
- Includes a dry-run mode that checks dataset IDs and variable names and estimates download sizes before anything is downloaded
- Logs every download, successful or failed, to a CSV file

## Requirements

- A free [Copernicus Marine account](https://data.marine.copernicus.eu/register)
- [Anaconda](https://www.anaconda.com/) or Miniconda
- `copernicusmarine` version 2 or later (the script checks this)

## Setup

Create the environment and log in. You only need to log in once.

```bash
conda create -n cmems -c conda-forge python=3.12 copernicusmarine
conda activate cmems
copernicusmarine login
```

## Configuration

Edit the settings at the top of `download_cmems.py`:

| Setting | Description | Default |
|---------|-------------|---------|
| `OUT_DIR` | Folder where files are saved | `~/Enviro layers` |
| `BBOX` | Longitude and latitude bounds | Lon −180 to 180, Lat −80 to −15 |
| `T0`, `T1` | Start and end dates | Currently set at 1 July 2025 to 30 September 2026 |
| `REQUESTS` | The datasets, variables and depths to download | See below |

## Products

| Short name | Contents | Variables | Dataset ID |
|------------|----------|-----------|------------|
| `sst` | Sea surface temperature | `analysed_sst`, `analysis_error`, `sea_ice_fraction` | `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` |
| `glorys` | Temperature, salinity, mixed layer depth, sea surface height (0–1 m) | `thetao`, `so`, `mlotst`, `zos` | `cmems_mod_glo_phy_my_0.083deg_P1D-m` |
| `chl` | Chlorophyll-a, gap-free daily | `CHL`, `CHL_uncertainty` | `cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D` |
| `pft` | Phytoplankton functional types, monthly (single file) | `CHL`, `DIATO`, `DINO`, `GREEN`, `HAPTO`, `MICRO`, `NANO`, `PICO`, `PROCHLO`, `PROKAR` | `cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1M` |
| `zoo` | Zooplankton carbon (0–1 m) | `zooc` | `cmems_mod_glo_bgc-plankton_anfc_0.25deg_P1D-m` |
| `wind` | Hourly wind | `eastward_wind`, `northward_wind` | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` |
| `ssh` | Sea level and geostrophic currents | `adt`, `sla`, `ugos`, `vgos`, `ugosa`, `vgosa` | `cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D` |
| `sic` | Sea ice concentration, Southern Hemisphere | `ice_conc` | `osisaf_obs-si_glo_phy-sic-south_nrt_amsr2_l4_P1D-m` |
| `siedge` | Sea ice edge, Southern Hemisphere | `ice_edge` | `osisaf_obs-si_glo_phy-siedge_nrt_sh-P1D` |

`wind` is excluded by default because its files are very large. Run a dry run first to check the size, then download it separately if needed.

## Usage

Run from the Anaconda Prompt with the `cmems` environment active.

**Check requests and estimate sizes (downloads nothing):**

```bash
python download_cmems.py --dry-run
```

This tests one chunk of every product, including `wind`, prints a summary table and saves it to `cmems_dry_run.csv` in the output folder.

**Download all default products (everything except `wind`):**

```bash
python download_cmems.py
```

**Download only specific products:**

```bash
python download_cmems.py --products wind
python download_cmems.py --products ssh sic siedge
```

## Output

Files are saved to `OUT_DIR` and named by product and month:

```
sst_202507.nc
sst_202508.nc
...
pft_202507-202609.nc   # single-file products cover the whole date range
```

Every attempt is recorded in `cmems_download_log.csv` (file, dataset, start, end, result). If a download fails, run the script again: completed files are skipped and failed months are retried.

## Adding a product

Add an entry to `REQUESTS`:

```python
dict(short="name", dataset="dataset-id",
     variables=["var1", "var2"], depth=None, chunk="month"),
```

- `depth`: `(min, max)` in metres for 3D products, or `None` for 2D products
- `chunk`: `"month"` for one file per month, or `"all"` for a single file covering the whole date range

Dataset IDs and variable names are listed on each product's page in the [Copernicus Marine Data Store](https://data.marine.copernicus.eu/products). Run `--dry-run` after adding a product to confirm the request works.

## Data acknowledgement

Data are provided by the Copernicus Marine Service. Please cite each product you use as described on its page in the Copernicus Marine Data Store.

## Author

Benjamin Viola, Monash University, Australia
