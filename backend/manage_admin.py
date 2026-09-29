"""Grant administrator access to an existing registered account."""
import argparse
import asyncio
import asyncpg
from settings import DATABASE_URL

async def grant(username):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("UPDATE users SET is_admin=TRUE WHERE username=$1 RETURNING username", username)
        if not row:
            raise SystemExit('Account not found. Register the account in the app first.')
        print(row['username'] + ' is now an administrator. Refresh the app if already signed in.')
    finally:
        await conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username', help='Existing account to make an administrator')
    asyncio.run(grant(parser.parse_args().username))
