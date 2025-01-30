import os
import CloudFlare
import waitress
import flask
from flask_httpauth import HTTPBasicAuth


app = flask.Flask(__name__)
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username == "nouser" and password == CLOUDFLARE_TOKEN:
        return username
    return None

@app.route('/nic/update', methods=['GET'])
@auth.login_required
def main():
    hostname = flask.request.args.get('hostname')
    ipv4 = flask.request.args.get('myip')
    zone = CLOUDFLARE_ZONE
    cf = CloudFlare.CloudFlare(token=CLOUDFLARE_TOKEN)

    if not hostname:
        return "bad", 400
    if not hostname.endswith(zone):
        return "bad", 400
    if not ipv4:
        return "bad", 400

    try:
        zones = cf.zones.get(params={'name': zone})

        if not zones:
            return "bad", 404

        record_zone_concat = hostname

        a_record = cf.zones.dns_records.get(zones[0]['id'], params={
                                            'name': record_zone_concat, 'match': 'all', 'type': 'A'})
        
        if not a_record:
            return "bad", 404


        if a_record[0]['content'] != ipv4:
            cf.zones.dns_records.put(zones[0]['id'], a_record[0]['id'], data={
                                     'name': a_record[0]['name'], 'type': 'A', 'content': ipv4, 'proxied': a_record[0]['proxied'], 'ttl': a_record[0]['ttl']})

    except CloudFlare.exceptions.CloudFlareAPIError as e:
        return "bad", 500

    return "good", 200

@app.route('/', methods=['GET'])
def fritz_box():
    token = flask.request.args.get('token')
    zone = flask.request.args.get('zone')
    record = flask.request.args.get('record')
    ipv4 = flask.request.args.get('ipv4')
    ipv6 = flask.request.args.get('ipv6')
    cf = CloudFlare.CloudFlare(token=token)

    if not token:
        return flask.jsonify({'status': 'error', 'message': 'Missing token URL parameter.'}), 400
    if not zone:
        return flask.jsonify({'status': 'error', 'message': 'Missing zone URL parameter.'}), 400
    if not ipv4 and not ipv6:
        return flask.jsonify({'status': 'error', 'message': 'Missing ipv4 or ipv6 URL parameter.'}), 400

    try:
        zones = cf.zones.get(params={'name': zone})

        if not zones:
            return flask.jsonify({'status': 'error', 'message': 'Zone {} does not exist.'.format(zone)}), 404

        record_zone_concat = '{}.{}'.format(record, zone) if record is not None else zone

        a_record = cf.zones.dns_records.get(zones[0]['id'], params={
                                            'name': record_zone_concat, 'match': 'all', 'type': 'A'})
        aaaa_record = cf.zones.dns_records.get(zones[0]['id'], params={
                                            'name': record_zone_concat, 'match': 'all', 'type': 'AAAA'})

        if ipv4 is not None and not a_record:
            return flask.jsonify({'status': 'error', 'message': f'A record for {record_zone_concat} does not exist.'}), 404

        if ipv6 is not None and not aaaa_record:
            return flask.jsonify({'status': 'error', 'message': f'AAAA record for {record_zone_concat} does not exist.'}), 404

        if ipv4 is not None and a_record[0]['content'] != ipv4:
            cf.zones.dns_records.put(zones[0]['id'], a_record[0]['id'], data={
                                     'name': a_record[0]['name'], 'type': 'A', 'content': ipv4, 'proxied': a_record[0]['proxied'], 'ttl': a_record[0]['ttl']})

        if ipv6 is not None and aaaa_record[0]['content'] != ipv6:
            cf.zones.dns_records.put(zones[0]['id'], aaaa_record[0]['id'], data={
                                     'name': aaaa_record[0]['name'], 'type': 'AAAA', 'content': ipv6, 'proxied': aaaa_record[0]['proxied'], 'ttl': aaaa_record[0]['ttl']})
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        return flask.jsonify({'status': 'error', 'message': str(e)}), 500

    return flask.jsonify({'status': 'success', 'message': 'Update successful.'}), 200

@app.route('/healthz', methods=['GET'])
def healthz():
    return flask.jsonify({'status': 'success', 'message': 'OK'}), 200


app.secret_key = os.urandom(24)
CLOUDFLARE_ZONE = os.environ.get('CLOUDFLARE_ZONE')
CLOUDFLARE_TOKEN = os.environ.get('CLOUDFLARE_TOKEN')
waitress.serve(app, host='0.0.0.0', port=80)
