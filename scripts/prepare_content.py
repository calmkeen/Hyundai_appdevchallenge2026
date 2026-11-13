"""Generate a clearly unverified development catalog, never a published vehicle manual."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    p = ROOT / "content" / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


locales = [
 ("ko-KR","한국어","한국어",False), ("en","English","영어",False),
 ("ja-JP","日本語","일본어",False), ("zh-Hans","简体中文","중국어 간체",False),
 ("zh-Hant","繁體中文","중국어 번체",False), ("de-DE","Deutsch","독일어",False),
 ("fr-FR","Français","프랑스어",False), ("es","Español","스페인어",False),
 ("pt-BR","Português (Brasil)","포르투갈어 브라질",False), ("pt-PT","Português","포르투갈어",False),
 ("it-IT","Italiano","이탈리아어",False), ("nl-NL","Nederlands","네덜란드어",False),
 ("ru-RU","Русский","러시아어",False), ("uk-UA","Українська","우크라이나어",False),
 ("pl-PL","Polski","폴란드어",False), ("cs-CZ","Čeština","체코어",False),
 ("sv-SE","Svenska","스웨덴어",False), ("da-DK","Dansk","덴마크어",False),
 ("nb-NO","Norsk","노르웨이어",False), ("fi-FI","Suomi","핀란드어",False),
 ("tr-TR","Türkçe","튀르키예어",False), ("ar","العربية","아랍어",True),
 ("he-IL","עברית","히브리어",True), ("fa-IR","فارسی","페르시아어",True),
 ("ur-PK","اردو","우르두어",True), ("hi-IN","हिन्दी","힌디어",False),
 ("bn-BD","বাংলা","벵골어",False), ("ta-IN","தமிழ்","타밀어",False),
 ("th-TH","ไทย","태국어",False), ("vi-VN","Tiếng Việt","베트남어",False),
 ("id-ID","Bahasa Indonesia","인도네시아어",False), ("ms-MY","Bahasa Melayu","말레이어",False),
 ("fil-PH","Filipino","필리핀어",False), ("mn-MN","Монгол","몽골어",False),
 ("kk-KZ","Қазақша","카자흐어",False), ("uz-UZ","O‘zbekcha","우즈베크어",False),
 ("km-KH","ខ្មែរ","크메르어",False), ("my-MM","မြန်မာ","미얀마어",False),
 ("ne-NP","नेपाली","네팔어",False), ("si-LK","සිංහල","싱할라어",False),
 ("el-GR","Ελληνικά","그리스어",False), ("hu-HU","Magyar","헝가리어",False),
 ("ro-RO","Română","루마니아어",False), ("bg-BG","Български","불가리아어",False),
 ("hr-HR","Hrvatski","크로아티아어",False), ("sk-SK","Slovenčina","슬로바키아어",False),
 ("sw-KE","Kiswahili","스와힐리어",False), ("lo-LA","ລາວ","라오어",False),
]
write("locales/catalog.json", [{"locale":tag,"native_name":native,"display_name":ko,"rtl":rtl,
    "ui_status":"DRAFT" if tag in ("ko-KR","en","ja-JP") else "PLANNED", "guide_status":"PLANNED",
    "mock_visible":tag in ("ko-KR","en","ja-JP")} for tag,native,ko,rtl in locales])
countries = {
 "KR":["ko-KR"],"US":["en","es"],"GB":["en"],"CA":["en","fr-FR"],"AU":["en"],"NZ":["en"],
 "JP":["ja-JP"],"CN":["zh-Hans"],"TW":["zh-Hant"],"HK":["zh-Hant","en"],"SG":["en","zh-Hans","ms-MY","ta-IN"],
 "MY":["ms-MY","en"],"TH":["th-TH"],"VN":["vi-VN"],"ID":["id-ID"],"PH":["fil-PH","en"],
 "IN":["hi-IN","en","ta-IN"],"BD":["bn-BD"],"PK":["ur-PK","en"],"LK":["si-LK","ta-IN"],"NP":["ne-NP"],
 "MN":["mn-MN"],"KZ":["kk-KZ","ru-RU"],"UZ":["uz-UZ"],"KH":["km-KH"],"MM":["my-MM"],
 "DE":["de-DE"],"FR":["fr-FR"],"ES":["es"],"IT":["it-IT"],"NL":["nl-NL"],"BE":["nl-NL","fr-FR","de-DE"],
 "CH":["de-DE","fr-FR","it-IT"],"AT":["de-DE"],"PT":["pt-PT"],"BR":["pt-BR"],"MX":["es"],"AR":["es"],
 "RU":["ru-RU"],"UA":["uk-UA"],"PL":["pl-PL"],"CZ":["cs-CZ"],"SE":["sv-SE"],"NO":["nb-NO"],"DK":["da-DK"],
 "FI":["fi-FI"],"TR":["tr-TR"],"SA":["ar"],"AE":["ar","en"],"IL":["he-IL","ar"],
}
write("locales/country-locales.json", {"status":"PLANNED","notes":"50개 지역의 개발용 커버리지 후보. 방문 통계 순위나 번역 지원 완료 목록이 아닙니다. 국가별 모든 언어를 망라하지 않습니다.","countries":countries})
profiles = []
for pid,code,name,year,market,steering in [
 ("demo-ioniq5-2024-kr","NE","IONIQ 5",2024,"KR","LEFT"),
 ("demo-ioniq5n-2025-gb","NE-N","IONIQ 5 N",2025,"GB","RIGHT")]:
    profiles.append({"profile_id":pid,"manufacturer":"Hyundai","model_code":code,"display_name":name,
       "model_year":year,"market_code":market,"powertrain":"BEV","option_codes":[],"steering_position":steering,
       "manual_set_id":None,"manual_version":None,"verification_status":"UNVERIFIED","support_contacts":[],"is_demo":True})
write("profiles/catalog.json",profiles)
write("glossary/catalog.json",{"version":"draft-1","status":"DRAFT","terms":[{"id":"ROW_1_LEFT","ko-KR":"앞좌석 왼쪽 문","en":"Front-left door"}]})
template=json.loads((ROOT/'contracts/guide.template.json').read_text())
write("guides/unpublished-template.json",template)
print(f"Wrote {len(locales)} language candidates and {len(countries)} market candidates (not published support).")
