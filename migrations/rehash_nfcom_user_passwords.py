"""
Fix user passwords in nfcom.users: detect unhashed or unrecognized-password-format values and re-hash using project scheme (bcrypt).
Usage:
    python migrations/rehash_nfcom_user_passwords.py --host localhost --user occ --password Altavista740

This script imports the project's password hashing helper to produce compatible hashes.
"""
import argparse
import pymysql
from app.core.security import pwd_context, get_password_hash


def connect(host, port, user, password, db):
    return pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', default='occ')
    parser.add_argument('--password', default='Altavista740')
    args = parser.parse_args()

    conn = connect(args.host, args.port, args.user, args.password, 'nfcom')
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, hashed_password FROM users')
            rows = cur.fetchall()

        updated = 0
        skipped = 0
        changed_ids = []
        conn.begin()
        with conn.cursor() as cur:
            for r in rows:
                uid = r['id']
                hp = r.get('hashed_password') or ''
                try:
                    scheme = pwd_context.identify(hp)
                except Exception:
                    scheme = None
                if scheme:
                    skipped += 1
                    continue
                # Not recognized: assume plaintext stored; re-hash
                new_hash = get_password_hash(hp)
                cur.execute('UPDATE users SET hashed_password=%s WHERE id=%s', (new_hash, uid))
                updated += 1
                changed_ids.append(uid)
        conn.commit()
        print(f'Passwords updated: {updated}, skipped (already valid): {skipped}')
        if changed_ids:
            print('Updated user ids (sample 20):', changed_ids[:20])
    finally:
        conn.close()

if __name__ == '__main__':
    main()
