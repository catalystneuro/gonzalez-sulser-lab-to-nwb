**Subject:** Gonzalez-Sulser × CatalystNeuro NWB conversion — info & metadata needed to start GRIN2B pipeline

**To:** Natalie Hung
**Cc:** Alfredo Gonzalez-Sulser, Ben Dichter
**From:** Alessandra Trapani

---

Hi Natalie,

Hope you're doing well! I've started looking through the data share you set up for us (`Gonzalez-Sulser-CN-data-share`) and have begun scaffolding the conversion pipeline against the GRIN2B line, as agreed in the SoW. To finalise the first end-to-end conversion of a GRIN2B session, I'd be grateful if you could help me fill a few gaps. I've grouped the requests by topic so you can answer whichever pieces are quickest first — anything you can send our way unblocks the next step.

---

### 1. TainiTec `.dat` binary format

The 21 `.dat` files in the share have no sidecar/header file we can find. To read them correctly we need confirmation of:

- **Sample rate** — we assume 250.4 Hz (TainiTec default). Correct?
- **Data type** — int16, little-endian?
- **Header bytes** — does each `.dat` have a fixed-size header before sample data, or is the file pure interleaved samples?
- **Channel layout** — are the 16 channels stored interleaved sample-by-sample? In what order are EEG vs EMG (e.g. `[EEG_1..EEG_14, EMG_1, EMG_2]` or some other arrangement)?
- **Conversion to volts** — what scale factor (gain) should we apply to convert the raw int16 values to volts/microvolts?
- **Reader code** — do you have an existing Python (or MATLAB) reader for TainiTec `.dat` files? A snippet would let us validate against a known-good output.

### 2. Filename convention

Filenames like `TAINI_1044_C_Grin2B_131_Baseline-2021_03_26-0000.dat` — could you confirm:

- `1044` = TainiTec transmitter/device ID?
- `C` = receiver slot or animal position?
- `131` = animal ID (matches `GRIN2B_131` in the seizure/sleep folders)?
- `2021_03_26` = recording start date (local Edinburgh time)?
- The `0000` suffix — file index for a multi-file session, or always `0000`?

### 3. Recording start time

To populate NWB `session_start_time` with timezone, we need the **time-of-day** the recording started for each session. The filename only encodes the date. Is there a log file, lab notebook, or convention (e.g. "always started at 9 AM Edinburgh time") we can use? If a per-session table exists, that would be perfect.

### 4. Electrode / probe configuration

- **NeuroNexus model number** of the EEG grid being used?
- **Anatomical targets** for each of the 14 EEG channels (channel-by-channel mapping to brain region/coordinates)?
- **EMG placement** — neck? trapezius? bilateral?
- **Reference / ground** strategy?
- A photo or schematic of the implant would be ideal.

### 5. Subject metadata

We don't see a subjects spreadsheet in the share. For each animal (GRIN2B_129, _130, …) we need:

- `subject_id` (already have)
- Species (rat, but please confirm strain — Long-Evans, Sprague-Dawley, Wistar?)
- Sex (M/F)
- Date of birth or age at recording
- Genotype (WT vs HET vs KO — the SFARI line variants)
- Weight at surgery / at recording
- Date of surgery (implant)
- Date of sacrifice
- Experimental group / treatment, if any

A simple CSV/Excel with one row per animal works perfectly.

### 6. BL1 / BL2 windowing

We see `Sample_start_end_GRIN2B.xlsx` listing BL1 and BL2 sample windows per file. Confirm:

- BL1 and BL2 are the **two consecutive 24-hour periods** extracted from each multi-day recording?
- Sample indices are zero-based offsets into the `.dat` file (not seconds)?
- What time-of-day does BL1 start at — lights-on (ZT0)? Or is the start arbitrary?

### 7. Light cycle

- Standard 12 h : 12 h L:D?
- What clock-time is lights-on at the Edinburgh facility?
- Is the cycle the same across all GRIN2B sessions and across the other 4 SFARI lines?

### 8. Sleep-state label encoding

In `*_BL1-dge_ok.csv` the column `sleep.score` contains integer codes. Which integers correspond to **Wake / NREM / REM / artifact**? (We see at least `0` — possibly Wake?)

### 9. Sleep scoring inputs (`*_Channels.csv`)

Each `Channels.csv` has 21.6 M rows × 2 columns (`Chanls1`, `Chanls2`) — exactly 24 h × 250.4 Hz. The first thousand rows are all zeros. Two questions:

- Are these the EEG and EMG channels selected from the raw `.dat` for sleep scoring? If so, **which** of the 14 EEG channels and which of the 2 EMG channels were used? (We'd then derive these from the raw `.dat` rather than re-publishing them.)
- Or are these something else (filtered? downsampled? z-scored)?

### 10. Power spectra (`*-pw_spectrum.csv`)

628 rows × 5 columns (`hz`, `s_0`, `s_1`, `s_2`, `s_4`). What do the `s_*` columns represent — power per sleep state? Why is `s_3` skipped?

### 11. Seizure CSV time reference

In `Seizure timestamps/GRIN2B_<id>_BL{1,2}_Seizures.csv` (cols `sec_start`, `sec_end`, `dur`):

- Are `sec_start` / `sec_end` measured from the **start of the BL window**, or from the **start of the raw `.dat`**, or from some absolute clock?
- Are the top-level `Seizures.csv` files identical to those inside the per-animal `seiz/` folder?

### 12. SWDs and ZT totals

Inside each `<animal>/seiz/` folder there are also `*_DGE_SWDs.csv` and `*_Seiz_Totals.csv`. Could you describe what each represents and how they were computed? I want to make sure we attach them to the right NWB processing module with the correct description.

### 13. Raw recordings vs. processed coverage

The share contains raw `.dat` files for ~21 sessions but processed sleep/seizure outputs for ~37 animals. Are the missing raw files:

- Stored elsewhere (different drive)?
- Lost / never archived?
- Not collected (animals only contributed processed data)?

If there's a path to the rest of the raw recordings, please share it — we'd like to convert all of them where possible.

### 14. Publication

The SoW notes the GRIN2B paper is published. Could you send the **DOI** (or PMID) and full citation? We'll attach it as `related_publications` on the NWB files and use the abstract for `experiment_description`.

### 15. Existing analysis / scoring code

Is the lab's automated sleep-detection and seizure-scoring code available in a repository (GitHub, GitLab, internal Edinburgh server)? Even a read-only link would help us interpret the processed CSVs correctly and avoid divergence.

### 16. Other 4 SFARI lines

After GRIN2B is solid we'll generalise the pipeline to the remaining lines. Could you let us know:

- The names of the other 4 lines?
- Which line is the next priority?
- Any known differences in protocol, channel count, or file naming for those lines?

---

Most of these are quick yes/no or short answers — anything you can send through this week would be hugely appreciated. Happy to schedule a short call if it's faster to walk through these together.

Thanks so much,
Alessandra

---
*CC: Ben Dichter — full conversion notes & repo scaffolding are in `gonzalez-sulser-lab-to-nwb/conversion_notes.md` (will push to GitHub once I get the green light to create the public repo).*
