# src/portfolioagent/client.py

import grpc
import agent_gateway_pb2
import agent_gateway_pb2_grpc
import json
import jwt
import time

# Use the same secret key as the server for testing
SECRET_KEY = "your-super-secret-key-that-is-not-in-code"


def generate_jwt(user_id: str):
    """Generates a short-lived JWT for a given user."""
    payload = {"user_id": user_id, "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def run_hitl_test(user_id: str, query_text: str, token: str):
    """Simulates a full Human-in-the-Loop workflow: propose and then confirm."""
    print(f"\n--- [Client] Simulating HITL Workflow for query: '{query_text}' ---")

    metadata = [("authorization", f"Bearer {token}")]

    try:
        with grpc.insecure_channel("localhost:8080") as channel:
            stub = agent_gateway_pb2_grpc.AgentGatewayStub(channel)

            # --- Step 1: Propose the Action ---
            print("\n[Client] Step 1: Proposing action...")
            propose_request = agent_gateway_pb2.ProposeActionRequest(
                user_id=user_id, query_text=query_text
            )
            propose_response = stub.ProposeAction(propose_request, metadata=metadata)

            print("✅ [Client] Received a proposal:")
            print(f"   Action ID: {propose_response.action_id}")
            print(f"   Explanation: {propose_response.explanation}")
            print(f"   Proposed Changes: {list(propose_response.proposed_changes)}")
            print(f"   Status: {propose_response.status_message}")

            # --- Step 2: Confirm the Action ---
            if propose_response.action_id:
                print("\n[Client] Step 2: Proposal looks good. Confirming action...")
                confirm_request = agent_gateway_pb2.ConfirmActionRequest(
                    user_id=user_id, action_id=propose_response.action_id
                )
                confirm_response = stub.ConfirmAction(
                    confirm_request, metadata=metadata
                )

                print("✅ [Client] Received a confirmation:")
                print(f"   Confirmation ID: {confirm_response.confirmation_id}")
                print(f"   Status: {confirm_response.status_message}")
            else:
                print("❌ [Client] Proposal failed pre-checks. Cannot confirm.")

    except grpc.RpcError as e:
        print(f"❌ [Client] An RPC error occurred: {e.details()}")


if __name__ == "__main__":
    test_user = "user-101"
    valid_token = generate_jwt(test_user)

    # Run the full workflow test.
    # The server's dummy logic will interpret this as a request to 'execute_trade'.
    run_hitl_test(
        user_id=test_user,
        query_text="Rebalance my portfolio to be more aggressive",
        token=valid_token,
    )
