"""
Tests for the Unsent mail-service integration.

The service authenticates with an HMAC-SHA256 signature rather than a bearer
token, so a mistake here is silent: mail simply stops arriving. These tests pin
the wire format against an independent reimplementation of the documented
signing scheme, so a refactor that changes the canonical message, the header
names, the "sha256=" prefix or the body encoding fails loudly.
"""
import hashlib
import hmac
import json
from unittest import mock

from django.test import TestCase, override_settings

from notifications.email_service import (
    build_email_payload,
    build_signed_headers,
    send_api_email,
)

API_KEY = 'test-key'
API_SECRET = 'test-secret'


def reference_signature(body_bytes, secret, timestamp, nonce):
    """
    Independent implementation of the documented scheme:

        bodyHash  = sha256_hex(body)
        canonical = "<timestamp>\\n<nonce>\\n<bodyHash>"
        signature = "sha256=" + hmac_sha256_hex(secret, canonical)
    """
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f'{timestamp}\n{nonce}\n{body_hash}'
    digest = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return f'sha256={digest}'


class SigningTests(TestCase):
    def test_signature_matches_the_documented_scheme(self):
        body = b'{"to":"a@b.com","subject":"s","html":"<p>h</p>","from_name":"Reportary"}'
        headers = build_signed_headers(
            body, API_KEY, API_SECRET, timestamp='1757660000', nonce='ab' * 16)

        self.assertEqual(
            headers['X-Signature'],
            reference_signature(body, API_SECRET, '1757660000', 'ab' * 16),
        )

    def test_all_five_headers_are_present(self):
        headers = build_signed_headers(b'{}', API_KEY, API_SECRET)
        self.assertEqual(
            set(headers),
            {'Content-Type', 'X-API-Key', 'X-Timestamp', 'X-Nonce', 'X-Signature'},
        )
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['X-API-Key'], API_KEY)

    def test_signature_carries_the_algorithm_prefix(self):
        """A bare hex digest is rejected by the service as an invalid signature."""
        headers = build_signed_headers(b'{}', API_KEY, API_SECRET)
        self.assertTrue(headers['X-Signature'].startswith('sha256='))
        self.assertEqual(len(headers['X-Signature']), len('sha256=') + 64)

    def test_nonce_is_32_hex_chars_and_single_use(self):
        first = build_signed_headers(b'{}', API_KEY, API_SECRET)['X-Nonce']
        second = build_signed_headers(b'{}', API_KEY, API_SECRET)['X-Nonce']
        self.assertRegex(first, r'^[0-9a-f]{32}$')
        self.assertNotEqual(first, second)

    def test_timestamp_is_unix_seconds(self):
        self.assertRegex(build_signed_headers(b'{}', API_KEY, API_SECRET)['X-Timestamp'],
                         r'^\d{10}$')

    def test_signature_covers_the_body(self):
        a = build_signed_headers(b'{"x":1}', API_KEY, API_SECRET,
                                 timestamp='1', nonce='a' * 32)['X-Signature']
        b = build_signed_headers(b'{"x":2}', API_KEY, API_SECRET,
                                 timestamp='1', nonce='a' * 32)['X-Signature']
        self.assertNotEqual(a, b)

    def test_signature_covers_timestamp_and_nonce(self):
        base = build_signed_headers(b'{}', API_KEY, API_SECRET,
                                    timestamp='1', nonce='a' * 32)['X-Signature']
        other_ts = build_signed_headers(b'{}', API_KEY, API_SECRET,
                                        timestamp='2', nonce='a' * 32)['X-Signature']
        other_nonce = build_signed_headers(b'{}', API_KEY, API_SECRET,
                                           timestamp='1', nonce='b' * 32)['X-Signature']
        self.assertNotEqual(base, other_ts)
        self.assertNotEqual(base, other_nonce)


@override_settings(MAIL_FROM_NAME='Reportary')
class PayloadTests(TestCase):
    def test_payload_uses_the_fields_the_service_expects(self):
        payload = build_email_payload('Subject', '<p>Body</p>', 'a@b.com')
        self.assertEqual(set(payload), {'to', 'subject', 'html', 'from_name'})
        self.assertEqual(payload['to'], 'a@b.com')
        self.assertEqual(payload['html'], '<p>Body</p>')

    def test_html_body_is_not_sent_under_the_old_body_key(self):
        """The previous service took `body`; this one silently ignores it."""
        self.assertNotIn('body', build_email_payload('s', '<p>h</p>', 'a@b.com'))

    def test_non_ascii_bodies_survive_encoding(self):
        """
        The app sends Japanese email. json.dumps returns a str, and handing a str
        to requests lets httplib encode it as latin-1, which raises on any
        non-ASCII character — so the body must be encoded to UTF-8 explicitly and
        the signature taken over those same bytes.
        """
        payload = build_email_payload('レポート', '<p>新しい報告があります</p>', 'a@b.com')
        body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

        headers = build_signed_headers(body, API_KEY, API_SECRET,
                                       timestamp='1', nonce='a' * 32)
        self.assertEqual(headers['X-Signature'],
                         reference_signature(body, API_SECRET, '1', 'a' * 32))
        body.decode('utf-8')  # round-trips


@override_settings(
    MAIL_API_KEY=API_KEY,
    MAIL_API_SECRET=API_SECRET,
    MAIL_API_ENDPOINT='https://unsent.example/api/send',
    MAIL_FROM_NAME='Reportary',
)
class DispatchTests(TestCase):
    """Exercise _send_via_api directly — send_api_email spawns daemon threads."""

    def _send(self, to_emails, cc_emails=None, subject='Subject', html='<p>hi</p>'):
        from notifications import email_service

        with mock.patch.object(email_service, 'requests') as fake_requests, \
                mock.patch.object(email_service, 'dispatch_disabled', return_value=False):
            fake_requests.post.return_value = mock.Mock(status_code=200)
            fake_requests.HTTPError = Exception
            email_service._send_via_api(subject, html, to_emails, cc_emails)
            return fake_requests.post

    def test_posts_signed_utf8_bytes_to_the_endpoint(self):
        post = self._send(['a@b.com'])
        post.assert_called_once()

        (url,), kwargs = post.call_args
        self.assertEqual(url, 'https://unsent.example/api/send')
        self.assertIsInstance(kwargs['data'], bytes)

        headers = kwargs['headers']
        self.assertEqual(
            headers['X-Signature'],
            reference_signature(kwargs['data'], API_SECRET,
                                headers['X-Timestamp'], headers['X-Nonce']),
            'the signature must cover exactly the bytes that are posted',
        )

    def test_body_round_trips_as_the_expected_json(self):
        post = self._send(['a@b.com'], subject='Hello', html='<p>Body</p>')
        payload = json.loads(post.call_args.kwargs['data'].decode('utf-8'))
        self.assertEqual(payload, {
            'to': 'a@b.com',
            'subject': 'Hello',
            'html': '<p>Body</p>',
            'from_name': 'Reportary',
        })

    def test_nothing_is_sent_without_credentials(self):
        with override_settings(MAIL_API_KEY='', MAIL_API_SECRET=''):
            self._send(['a@b.com']).assert_not_called()

    def test_nothing_is_sent_without_a_recipient(self):
        self._send([]).assert_not_called()


@override_settings(
    MAIL_API_KEY=API_KEY,
    MAIL_API_SECRET=API_SECRET,
    MAIL_API_ENDPOINT='https://unsent.example/api/send',
)
class FanOutTests(TestCase):
    def test_every_recipient_gets_their_own_request(self):
        """
        One request per address, so no recipient can see another's. `cc` is
        folded into the fan-out — the service has no cc field, and silently
        dropping those addresses would lose mail.
        """
        from notifications import email_service

        calls = []
        with mock.patch.object(email_service, 'threading') as fake_threading:
            fake_threading.Thread.side_effect = lambda target, args: calls.append(args) or mock.Mock()
            send_api_email('s', '<p>h</p>', ['a@b.com', 'b@b.com'], cc_emails=['c@b.com'])

        self.assertEqual([args[2] for args in calls],
                         [['a@b.com'], ['b@b.com'], ['c@b.com']])
        self.assertTrue(all(args[3] is None for args in calls))

    def test_duplicate_addresses_are_collapsed(self):
        from notifications import email_service

        calls = []
        with mock.patch.object(email_service, 'threading') as fake_threading:
            fake_threading.Thread.side_effect = lambda target, args: calls.append(args) or mock.Mock()
            send_api_email('s', '<p>h</p>', ['a@b.com'], cc_emails=['a@b.com', ' a@b.com '])

        self.assertEqual(len(calls), 1)
