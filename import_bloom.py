from blpapi import SessionOptions, Session, SubscriptionList, Event, Name #type: ignore

def handle_event(event, session):
    et = event.eventType()

    for msg in event:
        if et == Event.SESSION_STATUS:
            print("[SESSION]", msg.messageType(), msg.toString())

            if msg.messageType() == Name("SessionStarted"):
                print("Session started → subscribing")

                subs = SubscriptionList()
                subs.add("IBM US Equity",  "BID,ASK,LAST_PRICE")
                subs.add("MSFT US Equity", "BID,ASK,LAST_PRICE")

                session.subscribe(subs)

            elif msg.messageType() in (
                Name("SessionTerminated"),
                Name("SessionStartupFailure"),
            ):
                print("Session failed or terminated")
                session.stop()

        elif et == Event.SUBSCRIPTION_DATA:
            cid = msg.correlationId().value()
            if msg.hasElement("LAST_PRICE"):
                last = msg.getElement("LAST_PRICE").getValueAsFloat()
                print(f"[DATA] cid={cid} LAST_PRICE={last}")

        elif et == Event.SUBSCRIPTION_STATUS:
            print("[SUB_STATUS]", msg.toString())


def main():
    opts = SessionOptions()
    opts.setServerHost("localhost")
    opts.setServerPort(8194)

    session = Session(opts, eventHandler=handle_event)
    session.startAsync()

    input("Press ENTER to quit\n")
    session.stop()


if __name__ == "__main__":
    main()
