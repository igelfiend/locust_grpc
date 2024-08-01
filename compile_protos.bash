mkdir -p ./proto_cyrex
python3 -m grpc_tools.protoc -I./proto --python_out=./proto_cyrex --pyi_out=./proto_cyrex --grpc_python_out=./proto_cyrex ./proto/*.proto
