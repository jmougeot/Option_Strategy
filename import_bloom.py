from attr import dataclass
import blpapi 
from blpapi.event import Event
from blpapi.name import Name
from blpapi.subscriptionlist import SubscriptionList

@dataclass
class Option:
    host: str
    port: int 

options = Option(
    host= "localhost",
    port=8194
)

def EventHandler (Event, Session):
    return None 

sessionOptions = blpapi.sessionoptions.SessionOptions()
sessionOptions.setServerHost(options.host)
sessionOptions.setServerPort(options.port)

session = blpapi.session.Session(sessionOptions)
if not session.start():
    raise Exception("Can't start session.")

sessionOptions.setAutoRestartOnDisconnection(True)
sessionOptions.setNumStartAttempts(3)


session= blpapi.session.Session(sessionOptions)


def main(session: blpapi.session.Session):
    
    active= session.start()
    print(f"session est acitve : {active}")
    
    if active is False: 
        return None
    
    subs = SubscriptionList()
    subs.add("IBM US Equity", "BID,ASK,LAST_PRICE", "", 1)
    subs.add("MSFT US Equity", "BID,ASK,LAST_PRICE", "", 2)

    session.subscribe(subs)

    while True:
        ev = session.nextEvent()
        et = ev.eventType()
        for msg in ev:
            if et == Event.SUBSCRIPTION_DATA:
                cid = msg.correlationId().value()
                print(f"[DATA] cid={cid} {msg.topicName()} -> {msg.toString()}")
                if msg.hasElement("LAST_PRICE"):
                    last = msg.getElementAsFloat64("LAST_PRICE")
            elif et == Event.SUBSCRIPTION_STATUS:
                print(f"[SUB_STATUS] {msg.messageType()} cid={msg.correlationId().value()} {msg.toString()}")
            elif et == Event.SESSION_STATUS:
                print(f"[SESSION] {msg.messageType()} {msg.toString()}")
                if msg.messageType() in [Name("SessionTerminated"), Name("SessionStartupFailure")]:
                    session.stop()
                    return

if __name__ == "__main__":
    main(session)
