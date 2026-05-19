470 ocean rates for Export costing tool. It needs ocean rates by US origin hub + foreign destination. Our current 470 extract is missing a lot of lanes, so Export is erroring out.

We needed updated 470 Ocean Rates Extract.

WHAT WE NEED

For each country/city below, we need rates from these US origins where applicable:

- Dallas (WTX, DAL)
- Houston (WTXH, STX, HOU - Dallas OK if no Houston lane)
- Memphis (MR5)
- Savannah (ER5)

One row per carrier/contract is fine. We import the file as-is.

Biggest gaps in what we have now: Savannah and Memphis rows are often missing (we see Charleston, Dallas, Houston but not the hub we need). Example: China/Qingdao has Dallas, Houston, Memphis, Charleston - no Savannah.

---

FILE FORMAT

Same CSV header as always:

unOrig,unVia,unDest,orig,via,dest,dischargePort,scacCode,carrierName,contractNumber,rateType,amendmentNumber,effectiveDate,expirationDate,updateTime,40FT,40HC,DTHC40FT,DTHC40HC,ALLIN40FT,ALLIN40HC

---

COUNTRIES / CITIES (our Export list)

China - Qingdao, Xiamen, Nantong
Vietnam - Ho Chi Minh, Da Nang, Haiphong
Korea - Busan, Kwangyang
Japan - Osaka, Kobe, Nagoya
Malaysia - Tanjung Pelepas, Penang, Port Klang
Taiwan - Keelung, Taichung, Kaohsiung, Tao Yuan
Indonesia - Jakarta, Semarang, Cikarang, Surabaya
Thailand - Bangkok, Lat Krabang, Laem Chabang
Bangladesh - Chittagong
Pakistan - Port Qasim/Karachi
India - Mundra, Tuticorin, Chennai
Turkey - Iskenderun, Mersin, Izmir
Mexico - Yecapixtla, Parras, CD Victoria
Peru - Callao
Guatemala - Amatitlan, Palin
Honduras - Naco
Spain - Santa Barbara
Italy - Bergamo, Salerno
Other - Batumi

---

OPEN QUESTIONS

Mexico - We only see Manzanillo / Lazaro Cardenas in ocean data. Export uses Yecapixtla, Parras, CD Victoria. What discharge port should those map to? Can you include 470 rows for them?

Spain - We have Spain / Santa Barbara on Export but no matching port in ocean. Typo? Should it be Barcelona, Valencia, Algeciras, or something else?

---
