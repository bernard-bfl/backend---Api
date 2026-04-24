import re 
from typing import Optional

COUNTRY_MAP: dict[str, str] = {
    "nigeria": "NG", "nigerian": "NG",
    "ghana": "GH", "ghanaian": "GH",
    "kenya": "KE", "kenyan": "KE",
    "south africa": "ZA", "south african": "ZA",
    "ethiopia": "ET", "ethiopian": "ET",
    "egypt": "EG", "egyptian": "EG",
    "tanzania": "TZ", "tanzanian": "TZ",
    "uganda": "UG", "ugandan": "UG",
    "cameroon": "CM", "cameroonian": "CM",
    "senegal": "SN", "senegalese": "SN",
    "ivory coast": "CI", "ivorian": "CI",
    "angola": "AO", "angolan": "AO",
    "mozambique": "MZ", "mozambican": "MZ",
    "zambia": "ZM", "zambian": "ZM",
    "zimbabwe": "ZW", "zimbabwean": "ZW",
    "mali": "ML", "malian": "ML",
    "burkina faso": "BF", "burkinabe": "BF",
    "niger": "NE", "nigerien": "NE",
    "chad": "TD", "chadian": "TD",
    "sudan": "SD", "sudanese": "SD",
    "morocco": "MA", "moroccan": "MA",
    "algeria": "DZ", "algerian": "DZ",
    "tunisia": "TN", "tunisian": "TN",
    "libya": "LY", "libyan": "LY",
    "benin": "BJ", "beninese": "BJ",
    "togo": "TG", "togolese": "TG",
    "rwanda": "RW", "rwandan": "RW",
    "burundi": "BI", "burundian": "BI",
    "somalia": "SO", "somali": "SO",
    "eritrea": "ER", "eritrean": "ER",
    "gambia": "GM", "gambian": "GM",
    "guinea": "GN", "guinean": "GN",
    "sierra leone": "SL", "sierra leonean": "SL",
    "liberia": "LR", "liberian": "LR",
    "mauritania": "MR", "mauritanian": "MR",
    "cape verde": "CV", "cabo verde": "CV",
    "gabon": "GA", "gabonese": "GA",
    "dr congo": "CD", "drc": "CD",
    "congo": "CG",
    "madagascar": "MG", "malagasy": "MG",
    "malawi": "MW", "malawian": "MW",
    "botswana": "BW", "namibia": "NA",
    "namibian": "NA", "lesotho": "LS",
    "eswatini": "SZ", "swaziland": "SZ",
    "united states": "US", "usa": "US",
    "america": "US", "american": "US",
    "uk": "GB", "united kingdom": "GB",
    "britain": "GB", "british": "GB",
    "canada": "CA", "canadian": "CA",
    "france": "FR", "french": "FR",
    "germany": "DE", "german": "DE",
    "india": "IN", "indian": "IN",
    "china": "CN", "chinese": "CN",
    "brazil": "BR", "brazilian": "BR",
    "australia": "AU", "australian": "AU",
}
AGE_GROUP_MAP = {
    "child": "child", "children": "child",
    "teenager": "teenager", "teenagers": "teenager",
    "teen": "teenager", "teens": "teenager",
    "adult": "adult", "adults": "adult",
    "senior": "senior", "seniors": "senior",
}

class ParsedQuery:
    def __init__(self):
        self.gender: Optional[str] = None
        self.age_group: Optional[str] = None
        self.country_id: Optional[str] = None
        self.min_age: Optional[int] = None
        self.max_age: Optional[int] = None
        self.valid: bool = True
        self.error: Optional[str] = None

    def has_filters(self) -> bool:
        return any(
            v is not None
            for v  in [
                self.gender, self.age_group, self.country_id, self.min_age, self.max_age
            ]
        )
    
def parse_natural_language(query: str) -> ParsedQuery:
        result = ParsedQuery()
        q = query.lower().strip()

        if not q:
            result.valid = False
            result.error = "Unable to interpret query"
            return result
        
        #gender 
        both = re.search(r"\b(male and female|female and male|both genders?)\b", q)
        if both:
            result.gender = None
        elif re.search(r"\b(female|females|woman|women|girl|girls)\b", q):
            result.gender = "female"
        elif re.search(r"\b(male|males|man|men|boy|boys)\b", q):
            result.gender = "male"

        #agegroup
        for kw, grp in AGE_GROUP_MAP.items():
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, q):
                result.age_group = grp
                break
             
        #descriptive age words
        if re.search(r"\byoung\b", q):
            result.min_age = 16
            result.max_age = 24
        
        if re.search(r"\bmiddle[- ]aged\b", q):
            result.min_age = 35
            result.max_age = 54
        if re.search(r"\b(old|elderly)\b", q):
            result.min_age = 65

        #numeric age expressions 
        m = re.search(r"\bbetween\s+(\d+)\s+and\s+(\d+)\b", q)
        if m:
            result.min_age = int(m.group(1))
            result.max_age = int(m.group(2))

        m = re.search(r"\b(?:below|under|younger than|less than)s+(\d+)\b", q)
        if m:
            result.max_age = int(m.group(1))

        m = re.search(r"\b(?above|over|older than|greater than|more than)\s+(\d+)\b", q)
        if m:
            result.min_age = int(m.group(1))
        
        m = re.search(r"\bagged?\s+(\d+)\b", q)
        if m:
            result.min_age = int(m.group(1))
            result.max_age = int(m.group(1))

        #country (longest match first)
        sorted_countries = sorted(COUNTRY_MAP.keys(), key=len, reverse=True)
        for name in sorted_countries:
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, q):
                result.country_id = COUNTRY_MAP[name]
                break

        #validity
        if not result.has_filters():
            result.valid = False
            result.error = "Unable to interpret query"

        return result




            