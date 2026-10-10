"""Provider exceptions shared by routing and weather adapters. Messages never include keys."""


class ProviderError(Exception):
    code = "UPSTREAM_ERROR"
    status_code = 502


class ProviderNotConfigured(ProviderError):
    code = "ROUTING_NOT_CONFIGURED"
    status_code = 503


class ProviderRateLimited(ProviderError):
    code = "UPSTREAM_RATE_LIMITED"
    status_code = 429


class ProviderTimeout(ProviderError):
    code = "UPSTREAM_TIMEOUT"
    status_code = 504
