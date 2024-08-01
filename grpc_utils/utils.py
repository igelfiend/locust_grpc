import time
from typing import Any, Callable, Type

import grpc
import grpc._channel
import grpc.experimental.gevent as grpc_gevent
from grpc_interceptor import ClientInterceptor
from grpc_interceptor.client import _swap_args
from locust import User


# patch grpc so that it uses gevent instead of asyncio
grpc_gevent.init_gevent()


class LocustInterceptor(ClientInterceptor):
    def __init__(self, environment, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.env = environment

    def intercept_unary_unary(
        self,
        continuation: Callable,
        call_details: grpc.ClientCallDetails,
        request: Any,
    ):
        """
        Moved from `intercept` to process separately unary and stream.
        This one handles continuation as a regular function.
        """
        response = None
        exception = None
        start_perf_counter = time.perf_counter()
        response_length = 0
        try:
            response = _swap_args(continuation)(request, call_details)
            response_length = response.result().ByteSize()
        except grpc.RpcError as e:
            exception = e

        self.env.events.request.fire(
            request_type="grpc",
            name=call_details.method,
            response_time=(time.perf_counter() - start_perf_counter) * 1000,
            response_length=response_length,
            response=response,
            context=None,
            exception=exception,
        )
        return response

    def intercept_unary_stream(
        self,
        continuation: Callable,
        call_details: grpc.ClientCallDetails,
        request: Any,
    ):
        """
        Moved from `intercept` to process separately unary and stream.
        This one handles continuation as a generator.
        """
        response = None
        exception = None
        start_perf_counter = time.perf_counter()
        response_length = 0
        try:
            response = _swap_args(continuation)(request, call_details)
            for r in response:
                response_length += r.ByteSize()
                yield r
        except grpc.RpcError as e:
            exception = e

        self.env.events.request.fire(
            request_type="grpc",
            name=call_details.method,
            response_time=(time.perf_counter() - start_perf_counter) * 1000,
            response_length=response_length,
            response=response,
            context=None,
            exception=exception,
        )

    def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.ClientCallDetails,
    ):
        """
        Usually this one should be overriden, BUT
        Somehow official docs can't handle unary-stream rpc properly and hangs on a call.
        So we have to declare separate handlers for both unary-unary and unary-stream.
        """
        return method(request_or_iterator, call_details)


class GrpcUser(User):
    abstract = True

    def __init__(self, environment):
        super().__init__(environment)

        self._channel = grpc.insecure_channel(self.host)
        interceptor = LocustInterceptor(environment=environment)
        self._channel = grpc.intercept_channel(self._channel, interceptor)

    def setup_stub(self, stub_class: Type) -> object:
        return stub_class(self._channel)
