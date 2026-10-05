"""Run the local backend: python -m companion"""
import uvicorn

from companion.identity import DEFAULT_PORT


def main():
    uvicorn.run('companion.main:create_app', factory=True, host='127.0.0.1', port=DEFAULT_PORT)


if __name__ == '__main__':
    main()
