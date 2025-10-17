import blpapi
from blpapi import SessionOptions, Session

# -------- PARAMÈTRES À ADAPTER --------
TICKER = "EURH6C 97.50 Comdty"   # exemple : Call Euribor H6 97.50
FIELDS = ["OPT_DELTA", "OPT_GAMMA", "OPT_VEGA", "OPT_THETA", "OPT_RHO", "PX_LAST"]
# ---------------------------------------

# Connexion locale
options = SessionOptions()
options.setServerHost("localhost")
options.setServerPort(8194)

session = Session(options)
if not session.start():
    print("❌ Échec de connexion à Bloomberg.")
    exit()
session.openService("//blp/refdata")

service = session.getService("//blp/refdata")
request = service.createRequest("ReferenceDataRequest")
request.append("securities", TICKER)
for f in FIELDS:
    request.append("fields", f)

cid = session.sendRequest(request)

while True:
    ev = session.nextEvent()
    for msg in ev:
        if msg.messageType() == blpapi.Name("ReferenceDataResponse"):
            data = msg.getElement("securityData").getValue(0).getElement("fieldData")
            print(f"📊 Greeks pour {TICKER}")
            for f in FIELDS:
                try:
                    print(f"{f}: {data.getElementAsString(f)}")
                except:
                    print(f"{f}: N/A")
    if ev.eventType() == blpapi.Event.RESPONSE:
        break