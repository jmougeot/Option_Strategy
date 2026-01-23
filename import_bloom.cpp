#include <iostream>
#include <blpapi_event.h>
#include <blpapi_eventhandler.h>
#include <blpapi_message.h>
#include <blpapi_messageiterator.h>
#include <blpapi_name.h>
#include <blpapi_session.h>
#include <blpapi_sessionoptions.h>
#include <blpapi_subscriptionlist.h>
#include <blpapi_correlationid.h>
using namespace blpapi;



class SubscriptionEventHandler : public EventHandler {
public:
    void processEvent(const Event& event, Session* session) override {
        // Log event type
        std::cout << "== EventType: " << event.eventType() << std::endl;

        MessageIterator it(event);
        while (it.next()) {
            Message msg = it.message();
            std::cout << "  msgType=" << msg.messageType()
                      << "  cid=" << msg.correlationId() << std::endl;

            if (event.eventType() == Event::SUBSCRIPTION_DATA) {
                if (msg.hasElement("LAST_PRICE")) {
                    double last = msg.getElementAsFloat64("LAST_PRICE");
                    std::cout << "    LAST_PRICE=" << last << std::endl;
                }
            } else if (event.eventType() == Event::SUBSCRIPTION_STATUS) {
                // Expect SubscriptionStarted / SubscriptionFailure / SubscriptionTerminated
                msg.print(std::cout);
            } else if (event.eventType() == Event::SESSION_STATUS) {
                // Expect SessionStarted / SessionTerminated / SessionStartupFailure
                Name terminated("SessionTerminated");
                Name startupFail("SessionStartupFailure");
                if (msg.messageType() == terminated || msg.messageType() == startupFail) {
                    std::cout << "Session ending; calling stop()." << std::endl;
                    if (session) session->stop();
                }
            }
        }
    }
};

int main() {
    // Session options
    SessionOptions opts;
    opts.setServerHost("localhost");
    opts.setServerPort(8194);

    // Handler + async session
    SubscriptionEventHandler handler;
    Session session(opts, &handler);

    if (!session.startAsync()) {
        std::cerr << "Failed to start async session." << std::endl;
        return 1;
    }

    // Optionally open service explicitly; subscribe will also trigger it if needed
    // session.openServiceAsync("//blp/mktdata");

    // Build and submit subscriptions (after SessionStarted arrives)
    // For brevity submit immediately; in production, gate on SessionStarted
    SubscriptionList subs;
    subs.add("IBM US Equity",  "BID,ASK,LAST_PRICE", "", CorrelationId(1));
    subs.add("MSFT US Equity", "BID,ASK,LAST_PRICE", "", CorrelationId(2));
    session.subscribe(subs);

    std::cout << "Press ENTER to quit" << std::endl;
    (void)getchar();

    session.stop();  // Ensure clean shutdown
    return 0;
}
