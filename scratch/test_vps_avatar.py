import urllib.request
import urllib.error

data = b'0' * (3500 * 1024)
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
header = (
    '--' + boundary + '\r\n'
    'Content-Disposition: form-data; name="avatar"; filename="test.png"\r\n'
    'Content-Type: image/png\r\n\r\n'
).encode('utf-8')
footer = ('\r\n--' + boundary + '--\r\n').encode('utf-8')
body = header + data + footer

req = urllib.request.Request(
    'http://103.161.118.158/account/avatar/upload',
    data=body,
    headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'X-Requested-With': 'XMLHttpRequest'
    }
)
try:
    with urllib.request.urlopen(req) as resp:
        print('Status:', resp.status)
        print('Body:', resp.read().decode('utf-8', errors='ignore')[:300])
except urllib.error.HTTPError as e:
    print('HTTPError Status:', e.code)
    print('Error Body:', e.read().decode('utf-8', errors='ignore')[:300])
except Exception as e:
    print('Other error:', e)

