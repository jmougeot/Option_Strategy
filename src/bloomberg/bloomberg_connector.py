import blpapi

HOST, PORT = "localhost", 8194  # ← ton port détecté

opt = blpapi.SessionOptions()
opt.setServerHost(HOST)
opt.setServerPort(PORT)

sess = blpapi.Session(opt)

if not sess.start():
    print(f"❌ start() échec sur {HOST}:{PORT}")
else:
    print(f"✅ Session démarrée sur {HOST}:{PORT}")
    if not sess.openService("//blp/refdata"):
        print("❌ openService('//blp/refdata') échec")
    else:
        print("✅ Service refdata ouvert")
    sess.stop()