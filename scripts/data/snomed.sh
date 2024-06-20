#!/usr/bin/env bash

export NIH_API_KEY=""

curl -o snomed.zip "https://uts-ws.nlm.nih.gov/download?url=https://download.nlm.nih.gov/umls/kss/IHTSDO2024/IHTSDO20240501/SnomedCT_InternationalRF2_PRODUCTION_20240501T120000Z.zip&apiKey=$NIH_API_KEY"
unzip snomed.zip
mv SnomedCT_InternationalRF2_PRODUCTION_20240501T120000Z snomed
