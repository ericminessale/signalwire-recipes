"""Register an E911 address for a number.

Two REST calls. `POST /api/relay/rest/addresses` creates the emergency
address, with the nine fields the spec requires and `emergency_enabled` on.
`POST /api/relay/rest/phone_numbers/{id}/e911_address` attaches it to a number
by the address's id. The SDK wraps the first as `client.addresses.create`; the
second has no wrapper in 3.0.1, so this module sends it through the same HTTP
client the namespaces use.

Written against signalwire-sdk 3.0.1 (RestClient.addresses).
"""
from dotenv import load_dotenv
from signalwire.rest import RestClient

# the SDK does not read .env for you
load_dotenv()

# RestClient() reads SIGNALWIRE_PROJECT_ID / SIGNALWIRE_API_TOKEN /
# SIGNALWIRE_SPACE from the environment (signalwire/rest/client.py).
client = RestClient()


def create_address(label, first_name, last_name, street_number, street_name,
                   city, state, postal_code, country="US", **optional):
    """The emergency address. The nine positional fields are the spec's
    required list; `optional` takes address_type, address_number and the
    auto_correct_address flag."""
    return client.addresses.create(
        label=label, country=country, first_name=first_name, last_name=last_name,
        street_number=street_number, street_name=street_name, city=city,
        state=state, postal_code=postal_code, emergency_enabled=True, **optional)


def attach(phone_number_id, address_id):
    """Point a number at the address. No SDK helper in 3.0.1; the path is the
    spec's, sent through the client's HTTP layer."""
    return client.addresses._http.post(
        f"/api/relay/rest/phone_numbers/{phone_number_id}/e911_address",
        body={"e911_address_id": address_id})


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: python app.py <phone_number_id> <address_id>\n"
                         "create the address first with create_address() from a "
                         "Python shell, then attach it here")
    print(attach(sys.argv[1], sys.argv[2]))
