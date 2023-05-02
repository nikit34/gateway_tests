import requests


class Request:
    def __init__(self, method=None, path=None, headers=None, proxy=False):
        self.path = path
        self.method = method
        self.h = {"Content-Type": "application/json"} if headers is None \
            else headers
        self.proxy = proxy

    def __call__(self, f):
        def wrapper(obj, *args, **kwargs):
            payload = f(obj, *args, **kwargs)
            extra_path = ""
            if hasattr(obj, "token"):
                self.h["Authorization"] = "Bearer " + obj.token
            if hasattr(obj, "artifact_name") and self.method != "PUT":
                self.h["id"] = obj.artifact_name
            if hasattr(obj, "eTag") and hasattr(obj, "asset_id"):
                self.h["id"] = obj.asset_id
                self.h["If-Match"] = str(int(obj.eTag))
            if hasattr(obj, "artifact_name"):
                extra_path = "/" + obj.artifact_name
            if hasattr(obj, "onb") and hasattr(obj, "onboard"):
                if obj.onb and obj.onboard:
                    extra_path += "/boarding/configuration"
                elif obj.onb and not obj.onboard:
                    extra_path += "/boarding/offboard"
            if (payload is not None) and (self.method == "GET" or self.method == "DELETE"):
                dic_key = list(payload.keys())[0]
                path = "{}?{}={}".format(self.path + extra_path, dic_key, payload[dic_key])
                payload = None
            else:
                path = self.path + extra_path
            args = {
                "method": self.method,
                "url": 'https://{}/{}'.format(obj.host, path),
                "headers": self.h
            }
            if payload is not None:
                args["json"] = payload
            if self.proxy:
                proxy_lk = {
                   "http": "http://Permyakov_N:tDHF7Vx%21@127.0.0.1:3128",
                   "https": "http://Permyakov_N:tDHF7Vx%21@127.0.0.1:3128"
                }
                try:
                    result = requests.request(proxies=proxy_lk, **args)
                except requests.exceptions.ProxyError as err:
                    print("[ERROR] Proxy server is not available: ", err)
                    raise
            else:
                result = requests.request(**args)
            return result
        return wrapper
