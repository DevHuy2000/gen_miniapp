"""
FF VN Generator Core — dùng chung cho các API endpoint
Trích xuất từ gen_vn.py, bỏ phần UI/CLI, giữ nguyên logic
"""
import hmac, hashlib, requests, string, random, json, codecs, time, os
import base64, re, warnings
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# ── Protobuf (optional)
try:
    from google.protobuf import descriptor_pool, symbol_database
    from google.protobuf.internal import builder as _builder
    _sym_db = symbol_database.Default()
    DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(
        b'\n\x13MajorLoginRes.proto"\x87\x05\n\rMajorLoginRes\x12\x12\n\naccount_id\x18\x01 \x01(\x03\x12\x13\n\x0block_region\x18\x02 \x01(\t\x12\x13\n\x0bnoti_region\x18\x03 \x01(\t\x12\x11\n\tip_region\x18\x04 \x01(\t\x12\x19\n\x11\x61gora_environment\x18\x05 \x01(\t\x12\x19\n\x11new_active_region\x18\x06 \x01(\t\x12\r\n\x05token\x18\x08 \x01(\t\x12\x0b\n\x03ttl\x18\t \x01(\x05\x12\x12\n\nserver_url\x18\n \x01(\t\x12\x16\n\x0e\x65mulator_score\x18\x0c \x01(\x03\x12\x32\n\tblacklist\x18\r \x01(\x0b\x32\x1f.MajorLoginRes.BlacklistInfoRes\x12\x31\n\nqueue_info\x18\x0f \x01(\x0b\x32\x1d.MajorLoginRes.LoginQueueInfo\x12\x0e\n\x06tp_url\x18\x10 \x01(\t\x12\x15\n\rapp_server_id\x18\x11 \x01(\x03\x12\x0f\n\x07\x61no_url\x18\x12 \x01(\t\x12\x0f\n\x07ip_city\x18\x13 \x01(\t\x12\x16\n\x0eip_subdivision\x18\x14 \x01(\t\x12\x0b\n\x03kts\x18\x15 \x01(\x03\x12\n\n\x02\x61k\x18\x16 \x01(\x0c\x12\x0b\n\x03\x61iv\x18\x17 \x01(\x0c\x1aQ\n\x10\x42lacklistInfoRes\x12\x12\n\nban_reason\x18\x01 \x01(\x05\x12\x17\n\x0f\x65xpire_duration\x18\x02 \x01(\x03\x12\x10\n\x08\x62\x61n_time\x18\x03 \x01(\x03\x1a\x66\n\x0eLoginQueueInfo\x12\r\n\x05\x41llow\x18\x01 \x01(\x08\x12\x16\n\x0equeue_position\x18\x02 \x01(\x03\x12\x16\n\x0eneed_wait_secs\x18\x03 \x01(\x03\x12\x15\n\rqueue_is_full\x18\x04 \x01(\x08\x62\x06proto3'
    )
    _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
    _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'MajorLoginRes_pb2', globals())
except Exception:
    pass

# ── Config
REGION    = "VN"
LANG_CODE = "vi"
VN_CONFIG = {
    "guest_url":        "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant",
    "major_login_url":  "https://loginbp.ggpolarbear.com/MajorLogin",
    "get_login_url":    "https://clientbp.ggpolarbear.com/GetLoginData",
    "register_url":     "https://loginbp.ggpolarbear.com/MajorRegister",
    "choose_region_url":"https://loginbp.ggpolarbear.com/ChooseRegion",
    "veteran_url":      "https://clientbp.ggpolarbear.com/ActiveBeginnerGuide",
    "client_host":      "clientbp.ggpolarbear.com",
}

MAIN_HEX_KEY = "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
API_POOL     = [{"id": "100067", "key": bytes.fromhex(MAIN_HEX_KEY), "label": f"API {i:02d}"} for i in range(1, 8)]
AES_KEY      = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV       = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

ACCOUNT_NAME   = "Senzu"
PASSWORD_PRE   = "Senzu_999"
RARITY_THRESH  = 3

# ── Crypto
def varint(n):
    if n < 0: return b''
    out = []
    while True:
        b = n & 0x7F; n >>= 7
        if n: b |= 0x80
        out.append(b)
        if not n: break
    return bytes(out)

def proto_variant(fn, v): return varint((fn << 3) | 0) + varint(v)
def proto_length(fn, v):
    enc = v.encode() if isinstance(v, str) else v
    return varint((fn << 3) | 2) + varint(len(enc)) + enc

def build_proto(fields):
    pkt = bytearray()
    for fn, v in fields.items():
        if isinstance(v, dict):
            nested = build_proto(v)
            pkt.extend(proto_length(fn, nested))
        elif isinstance(v, int):
            pkt.extend(proto_variant(fn, v))
        else:
            pkt.extend(proto_length(fn, v))
    return bytes(pkt)

def aes_encrypt(hex_data: str) -> str:
    raw = bytes.fromhex(hex_data)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(raw, AES.block_size)).hex()

def aes_encrypt_bytes(hex_data: str) -> bytes:
    return bytes.fromhex(aes_encrypt(hex_data))

def decode_jwt(token: str) -> str:
    try:
        part = token.split(".")[1]
        part += "=" * ((4 - len(part) % 4) % 4)
        data = json.loads(base64.urlsafe_b64decode(part))
        return str(data.get("account_id") or data.get("external_id") or "N/A")
    except Exception:
        return "N/A"

def encode_open_id(original: str):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
          0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return "".join(chr(ord(c) ^ ks[i % len(ks)]) for i, c in enumerate(original))

def to_unicode_escaped(s):
    return "".join(c if 32 <= ord(c) <= 126 else "\\u{:04x}".format(ord(c)) for c in s)

# ── Name / Password generators
def gen_name():
    exp = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}
    num = f"{random.randint(1,99999):05d}"
    return f"{ACCOUNT_NAME[:7]}{''.join(exp[d] for d in num)}"

def gen_password():
    chars = string.ascii_uppercase + string.digits
    return PASSWORD_PRE + "".join(random.choices(chars, k=5))

# ── Rarity
RARITY_PATTERNS = {
    "REPEATED_DIGITS_4": (r"(\d)\1{3,}", 3),
    "SEQUENTIAL_5":      (r"(12345|23456|34567|45678|56789)", 4),
    "SEQUENTIAL_4":      (r"(0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210)", 3),
    "PALINDROME_6":      (r"^(\d)(\d)(\d)\3\2\1$", 5),
    "PALINDROME_4":      (r"^(\d)(\d)\2\1$", 3),
    "SPECIAL_HIGH":      (r"(1337|007|69|420)", 4),
    "QUADRUPLE":         (r"(1111|2222|3333|4444|5555|6666|7777|8888|9999|0000)", 4),
    "MIRROR":            (r"^(\d{2,3})\1$", 3),
    "GOLDEN":            (r"1618|0618", 3),
    "LOW_6_DIGITS":      (r"^\d{1,6}$", 3),
}

def check_rarity(acc: dict):
    aid = acc.get("account_id", "")
    if not aid or aid == "N/A":
        return False, None, None, 0
    score = 0; patterns = []
    for name, (pat, pts) in RARITY_PATTERNS.items():
        if re.search(pat, aid):
            score += pts; patterns.append(name)
    digits = [int(d) for d in aid if d.isdigit()]
    if len(set(digits)) == 1 and len(digits) >= 4:
        score += 5; patterns.append("UNIFORM")
    if len(digits) >= 4:
        diffs = [digits[i+1]-digits[i] for i in range(len(digits)-1)]
        if len(set(diffs)) == 1:
            score += 4; patterns.append("ARITHMETIC")
    if len(aid) <= 8 and aid.isdigit() and int(aid) < 1_000_000:
        score += 3; patterns.append("LOW_ID")
    if score >= RARITY_THRESH:
        return True, "RARE", f"ID={aid}|Score={score}|{','.join(patterns)}", score
    return False, None, None, score

# ── API steps
def step_register(session, password):
    api = random.choice(API_POOL)
    app_id = api["id"]; key = api["key"]
    data = f"password={password}&client_type=2&source=2&app_id={app_id}"
    sig  = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
    hdrs = {
        "User-Agent":      "GarenaMSDK/4.0.19P8(ASUS_Z01QD ;Android 12;en;US;)",
        "Authorization":   f"Signature {sig}",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip",
        "Connection":      "Keep-Alive",
    }
    r = session.post(f"https://{app_id}.connect.garena.com/oauth/guest/register",
                     headers=hdrs, data=data, timeout=15, verify=False)
    r.raise_for_status()
    j = r.json()
    if "uid" not in j: return None, None, None
    return j["uid"], api, j

def step_token(session, uid, password, api):
    app_id = api["id"]; key = api["key"]
    body = {"uid": uid, "password": password, "response_type": "token",
            "client_type": "2", "client_secret": key, "client_id": app_id}
    hdrs = {
        "Accept-Encoding": "gzip", "Connection": "Keep-Alive",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Host":            f"{app_id}.connect.garena.com",
        "User-Agent":      "GarenaMSDK/4.0.19P8(ASUS_Z01QD ;Android 12;en;US;)",
    }
    r = session.post(f"https://{app_id}.connect.garena.com/oauth/guest/token/grant",
                     headers=hdrs, data=body, timeout=15, verify=False)
    r.raise_for_status()
    j = r.json()
    if "open_id" not in j: return None, None
    return j["access_token"], j["open_id"]

def step_major_register(session, access_token, open_id, name, uid, password, api):
    enc    = encode_open_id(open_id)
    field  = codecs.decode(to_unicode_escaped(enc), "unicode_escape").encode("latin1")
    payload = build_proto({
        1: name, 2: access_token, 3: open_id,
        5: 102000007, 6: 4, 7: 1, 13: 1,
        14: field, 15: LANG_CODE, 16: 1, 17: 1
    })
    enc_payload = aes_encrypt_bytes(payload.hex())
    hdrs = {
        "Accept-Encoding": "gzip", "Authorization": "Bearer",
        "Connection":      "Keep-Alive",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Expect":          "100-continue",
        "Host":            "loginbp.ggblueshark.com",
        "ReleaseVersion":  "OB52",
        "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA":            "v1 1",
        "X-Unity-Version": "2018.4.",
    }
    r = session.post(VN_CONFIG["register_url"], headers=hdrs, data=enc_payload,
                     verify=False, timeout=15)
    return r.status_code == 200

def step_major_login(session, access_token, open_id):
    payload_parts = [
        b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02',
        LANG_CODE.encode("ascii"),
        b'\xb2\x01 afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xba\x01\x101d8ec0240ede109973f3321b9354b44d'
    ]
    data = b"".join(payload_parts)
    data = data.replace(b"afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390", access_token.encode())
    data = data.replace(b"1d8ec0240ede109973f3321b9354b44d", open_id.encode())
    enc  = aes_encrypt_bytes(data.hex())
    hdrs = {
        "Accept-Encoding": "gzip", "Authorization": "Bearer",
        "Connection":      "Keep-Alive",
        "Content-Type":    "application/x-www-form-urlencoded",
        "Expect":          "100-continue",
        "Host":            "loginbp.ggblueshark.com",
        "ReleaseVersion":  "OB52",
        "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1", "X-Unity-Version": "2018.4.11f1",
    }
    r = session.post(VN_CONFIG["major_login_url"], headers=hdrs, data=enc,
                     verify=False, timeout=15)
    if r.status_code == 200 and len(r.text) > 10:
        idx = r.text.find("eyJ")
        if idx != -1:
            jwt = r.text[idx:]
            d2  = jwt.find(".", jwt.find(".")+1)
            if d2 != -1:
                return jwt[:d2+44]
    return None

def step_bind_vn(session, jwt_token):
    try:
        data = build_proto({1: "VN"})
        enc  = aes_encrypt_bytes(data.hex())
        hdrs = {
            "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 12; M2101K7AG Build/SKQ1.210908.001)",
            "Connection":      "Keep-Alive", "Accept-Encoding": "gzip",
            "Content-Type":    "application/x-www-form-urlencoded",
            "Expect":          "100-continue", "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1", "X-GA": "v1 1", "ReleaseVersion": "OB52",
        }
        r = session.post(VN_CONFIG["choose_region_url"], data=enc,
                         headers=hdrs, verify=False, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def step_veteran(session, jwt_token):
    try:
        data = build_proto({1: 3})
        enc  = aes_encrypt_bytes(data.hex())
        hdrs = {
            "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 12; M2101K7AG Build/SKQ1.210908.001)",
            "Connection":      "Keep-Alive", "Accept-Encoding": "gzip",
            "Content-Type":    "application/x-www-form-urlencoded",
            "Expect":          "100-continue", "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1", "X-GA": "v1 1", "ReleaseVersion": "OB52",
        }
        r = session.post(VN_CONFIG["veteran_url"], data=enc,
                         headers=hdrs, verify=False, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def step_get_login_data(session, jwt_token, access_token):
    try:
        parts = jwt_token.split(".")
        p = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        jd = json.loads(base64.urlsafe_b64decode(p))
        ext_id  = jd["external_id"]
        sig_md5 = jd["signature_md5"]
        now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = bytes.fromhex("1a13323032352d30372d33302031313a30323a3531220966726565206669726528013a07312e3132302e32422c416e64726f6964204f5320372e312e32202f204150492d323320284e32473438482f373030323530323234294a0848616e6468656c645207416e64726f69645a045749464960c00c68840772033332307a1f41524d7637205646507633204e454f4e20564d48207c2032343635207c203480019a1b8a010f416472656e6f2028544d292036343092010d4f70656e474c20455320332e319a012b476f6f676c657c31663361643662372d636562342d343934622d383730622d623164616364373230393131a2010c3139372e312e31322e313335aa0102656eb201203939366136323964626364623339363462653662363937386635643831346462ba010134c2010848616e6468656c64ea014066663930633037656239383135616633306134336234613966363031393531366530653463373033623434303932353136643064656661346365663531663261f00101ca0207416e64726f6964d2020457494649ca03203734323862323533646566633136343031386336303461316562626665626466e003daa907e803899b07f003bf0ff803ae088004999b078804daa9079004999b079804daa907c80403d204262f646174612f6170702f636f6d2e6474732e667265656669726574682d312f6c69622f61726de00401ea044832303837663631633139663537663261663465376665666630623234643964397c2f646174612f6170702f636f6d2e6474732e667265656669726574682d312f626173652e61706bf00403f804018a050233329a050a32303139313138363933b205094f70656e474c455332b805ff7fc00504e005dac901ea0507616e64726f6964f2055c4b71734854394748625876574c6668437950416c52526873626d43676542557562555551317375746d525536634e30524f3751453141486e496474385963784d614c575437636d4851322b7374745279377830663935542b6456593d8806019006019a060134a2060134")
        payload = payload.replace(b"2025-07-30 11:02:51", now.encode())
        payload = payload.replace(b"ff90c07eb9815af30a43b4a9f6019516e0e4c703b44092516d0defa4cef51f2a", access_token.encode("utf-8"))
        payload = payload.replace(b"996a629dbcdb3964be6b6978f5d814db", ext_id.encode("utf-8"))
        payload = payload.replace(b"7428b253defc164018c604a1ebbfebdf", sig_md5.encode("utf-8"))
        enc     = aes_encrypt_bytes(payload.hex())
        hdrs = {
            "Expect":          "100-continue", "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1", "X-GA": "v1 1", "ReleaseVersion": "OB52",
            "Content-Type":    "application/x-www-form-urlencoded",
            "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Host":            VN_CONFIG["client_host"],
            "Connection":      "close", "Accept-Encoding": "gzip, deflate, br",
        }
        r = session.post(VN_CONFIG["get_login_url"], headers=hdrs,
                         data=enc, verify=False, timeout=12)
        return r.status_code == 200
    except Exception:
        return False

# ── Main pipeline
def create_one_account(auto_activate=True):
    """Tạo 1 acc VN hoàn chỉnh, trả về dict hoặc None nếu thất bại"""
    session = requests.Session()
    try:
        password = gen_password()
        name     = gen_name()

        uid, api, _ = step_register(session, password)
        if not uid: return None

        access_token, open_id = step_token(session, uid, password, api)
        if not access_token: return None

        if not step_major_register(session, access_token, open_id, name, uid, password, api):
            return None

        jwt = step_major_login(session, access_token, open_id)
        account_id = decode_jwt(jwt) if jwt else "N/A"

        if jwt and account_id != "N/A":
            step_bind_vn(session, jwt)
            step_veteran(session, jwt)

        acc = {
            "uid": uid,
            "password": password,
            "name": name,
            "region": REGION,
            "account_id": account_id,
            "jwt_token": jwt or "",
            "api": api["label"],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "activated": False,
        }

        is_rare, rtype, reason, score = check_rarity(acc)
        acc["rare"]         = is_rare
        acc["rare_reason"]  = reason or ""
        acc["rare_score"]   = score

        if auto_activate and jwt:
            ok = step_get_login_data(session, jwt, access_token)
            acc["activated"] = ok

        return acc

    except Exception as e:
        return None
    finally:
        session.close()
