from typing import Union

from fastapi import FastAPI
from engagement import stellarAPI

app = FastAPI()
sa = stellarAPI()

sa.params = {}

@app.get("/")
def simulate_engagement():
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
    return {"txResponse":txResponse}


@app.get("/getaccount/{account}")
def getaccount(account: str):
    sa.params["account"] = account
    
    try:
        account_details = sa.getAccount(sa.params)
        return {"account_details":account_details}
    except Exception as error:
        print("error: ", error)
        return {}

@app.get("/createclaim/{freelancer_account_public}")
def cClaim(freelancer_account_public: str, s: Union[str, None] = None, ep: Union[int, None] = None, ef: Union[str, None] = None):
    sa.params["freelancer_account_public"] = freelancer_account_public
    sa.params["client_account_secret"] = s
    sa.params["engagement_fee"] = ef
    sa.params["engagement_period"] = ep
    
    try:
        sa.engagementPersonas(sa.params)
        sa.createClaimableBalance(sa.params)
        balanceId = sa.getClaimableBalanceID(sa.params)
        return {"balanceId":balanceId}
    except Exception as error:
        print("error: ", error)
        return {}


@app.get("/getclaim/{freelancer_account_public}")
def gClaim(freelancer_account_public: str, s: Union[str, None] = None, balanceId: Union[str, None] = None):
    sa.params["freelancer_account_public"] = freelancer_account_public
    sa.params["client_account_secret"] = s
    
    try:
        sa.engagementPersonas(sa.params)
        txResponse = sa.claimBalance(sa.params, balanceId)
        return {"txResponse":txResponse}
    except Exception as error:
        print("error: ", error)
        return {}








