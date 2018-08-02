Examples
========

To install the dependencies for **all** the examples (they should not conflict), run: `pip install -r examples/**/requirements.txt`. Otherwise, refer to the respective `README.md` in each directory for specific instructions.


- [SWAPI Proxy](./swapi-proxy): A graphql server example which proxies all requests to [SWPAPI](https://swapi.co) and generates the runtime schema from an SDL. Uses [Flask](http://flask.pocoo.org/) and [requests](http://docs.python-requests.org/en/master/) and threads for concurrency.
- [SWAPI Aiohttp Proxy](./swapi-proxy-aiohttp): A graphql server example based on [Aiohttp](https://aiohttp.readthedocs.io/en/stable/) which proxies all requests to [SWPAPI](https://swapi.co) and generates the runtime schema from an SDL.
