import re
import json
import time
import datetime
import requests

from time import sleep

# Claimable balance methods
from stellar_sdk.xdr import TransactionResult, OperationType
from stellar_sdk.exceptions import NotFoundError, BadResponseError, BadRequestError
from stellar_sdk import Keypair, Network, Server, TransactionBuilder, Transaction, Asset, Operation
from stellar_sdk import Claimant, ClaimPredicate, CreateClaimableBalance, ClaimClaimableBalance



###################################
# Stellar API
###################################
class stellarAPI():
    def __init__(self):
        self.base_url = 'https://horizon-testnet.stellar.org/'

    ### Create an Account
    def createAccount(self, params):  
        starting_balance = params['starting_balance']
        secret = params["seed"]
       
        server = Server(horizon_url=self.base_url)
        source = Keypair.from_secret(secret)
        destination = Keypair.random()
       
        source_account = server.load_account(account_id=source.public_key)
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_create_account_op(
                destination=destination.public_key, starting_balance=starting_balance
            )
            .set_timeout(30)
            .build()
        )
        transaction.sign(source)
        response = server.submit_transaction(transaction)
        print(f"Transaction hash: {response['hash']}")
        print(
            f"New Keypair: \n\taccount id: {destination.public_key}\n\tsecret seed: {destination.secret}"
        )

    ### Get Account details based on Public Key
    def getAccount(self, params):
        account  = params["account"]
        endpoint = "accounts/"
        api_url = self.base_url + endpoint + account

        response = requests.get(api_url)
        return response.json()

    ### Retrieve Accounts involved in the engagement; e.g., Freelancer and Client
    def engagementPersonas(self, params):
        self.server = Server(self.base_url)

        client_account_secret = params["client_account_secret"]
        freelancer_account_public = params["freelancer_account_public"]

        self.A = Keypair.from_secret(client_account_secret)
        self.B = Keypair.from_public_key(freelancer_account_public)
       
        # NOTE: Proper error checks are omitted for brevity; always validate things!
       
        try:
            self.aAccount = self.server.load_account(self.A.public_key)
        except NotFoundError:
            raise Exception(f"Failed to load {self.A.public_key}")
       
    ### Create the contractual MOU and submit engagement fee to escrow until freelancer completes the job
    def createClaimableBalance(self, params):
        # Create a claimable balance with our two above-described conditions.
        engagement_period = params["engagement_period"]
        engagement_fee = params["engagement_fee"]

        print("1) Engagement beginning between freelancer and client.")
        print("### Client account: {0}".format(self.A.public_key))
        print("### Freelancer account: {0}".format(self.B.public_key))
        print("\n")
       
        soon = int(time.time() + engagement_period)
        bCanClaim = ClaimPredicate.predicate_before_relative_time(engagement_period)
        aCanClaim = ClaimPredicate.predicate_not(
            ClaimPredicate.predicate_before_absolute_time(soon)
        )
       
        # Create the operation and submit it in a transaction.
        claimableBalanceEntry = CreateClaimableBalance(
            asset = Asset.native(),
            amount = engagement_fee,
            claimants = [
                Claimant(destination = self.B.public_key, predicate = bCanClaim),
                Claimant(destination = self.A.public_key, predicate = aCanClaim)
            ]
        )
       
        self.tx = (
            TransactionBuilder (
                source_account = self.aAccount,
                network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee = self.server.fetch_base_fee()
            )
            .append_operation(claimableBalanceEntry)
            .set_timeout(180)
            .build()
        )
       
        self.tx.sign(self.A)
        try:
            self.txResponse = self.server.submit_transaction(self.tx)
            print("2) Engagement Fees have been successfuly escrowed.")
            print("### Engagement Fees: {0} (Asset Native)".format(engagement_fee))
            print("\n")
        except (BadRequestError, BadResponseError) as err:
            print(f"Tx submission failed: {err}")

    ### Assess completion of the job by the freelancer and determine who receive the claim/escrow
    def getClaimableBalanceID(self, params):
        txResult = TransactionResult.from_xdr(self.txResponse["result_xdr"])
        results = txResult.result.results
       
        # We look at the first result since our first (and only) operation
        # in the transaction was the CreateClaimableBalanceOp.
        operationResult = results[0].tr.create_claimable_balance_result
        balanceId = operationResult.balance_id.to_xdr_bytes().hex()
       
        # Method 3: Account B could alternatively do something like:
        try:
            balances = (
                self.server
                .claimable_balances()
                .for_claimant(self.B.public_key)
                .limit(1)
                .order(desc = True)
                .call()
            )
        except (BadRequestError, BadResponseError) as err:
            print(f"Claimable balance retrieval failed: {err}")

        return balanceId

    ### Assess completion of the job by the freelancer and determine who receive the claim/escrow
    def claimBalance(self, params, balanceId):
        sleep(3)
        
        # Just in case account data is not persisted
        try:
            self.A.public_key
        except:
            self.engagementPersonas(params)
       
        claimBalance = ClaimClaimableBalance(balance_id = balanceId)

        ## Future code updates will create conditions for freelancer to prove job was complete in order to claim the balance.
        print("3) Client attempting to claim balance due to incomplete job by freelancer.")
        print("### Client Account: {0}".format(self.A.public_key))
        print("### Balance ID: {0}".format(balanceId))
        print("\n")
       
        tx = (
            TransactionBuilder (
                source_account = self.aAccount,
                network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee = self.server.fetch_base_fee()
            )
            .append_operation(claimBalance)
            .set_timeout(180)
            .build()
        )
       
        tx.sign(self.A)
        try:
            txResponse = self.server.submit_transaction(tx)
            self.txResponse = txResponse
            print("4) Client successfully reclaimed balance due to incomplete job by freelancer.")
            print("### Transaction response: {0}".format(txResponse))
        except (BadRequestError, BadResponseError) as err:
            print(f"Tx submission failed: {err}")
            txResponse = ""

        return txResponse



       
##############################
##### Run Integration Test
##############################
if False:
    params = {
                "client_account_secret"     : "SDTPVQL4W6PAVATGBVAVMUM7M33M5FG477J2ITI5F2X5H5J7ZVFSGPCN",
                "freelancer_account_public" : "GA2I737YANJPZRGMMQML34TG3Z6IFEHAL4ZWBXSGCPMB5XMANG5GJEVA",
                "account"                   : "GBZVCPFEDZO6ONBHDNH3S5KFI6GDCCZACIYHXXIHCK3AM54NDV5HIK3U", # client public account
                "starting_balance"          : "5000",
                "engagement_period"         : 2, # Engagement period set to 2 seconds for demo purposes
                "engagement_fee"            : "300" # Cost of the Freelance engagement to be paid by the Client
    }
    
    
    sa = stellarAPI()
    
    
    sa.engagementPersonas(params)
    sa.createClaimableBalance(params)
    balanceId = sa.getClaimableBalanceID(params)
    txResponse = sa.claimBalance(params, balanceId)