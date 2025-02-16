r"""
                                                             
        _____                                               
  _____/ ____\______ ________________    ____   ___________ 
 /  _ \   __\/  ___// ___\_  __ \__  \  /  _ \_/ __ \_  __ \
(  <_> )  |  \___ \\  \___|  | \// __ \(  <_> )  ___/|  | \/
 \____/|__| /____  >\___  >__|  (____  /\____/ \___  >__|   
                 \/     \/           \/            \/         
"""

import asyncio
from itertools import chain
import logging
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    SpinnerColumn
)
from rich.style import Style

import arrow
console=Console()
from tenacity import retry,stop_after_attempt,wait_random,retry_if_not_exception_type
from ..constants import subscriptionsEP,NUM_TRIES
import ofscraper.constants as constants
log=logging.getLogger("shared")
import ofscraper.classes.sessionbuilder as sessionbuilder
import ofscraper.utils.args as args_


async def get_subscriptions(subscribe_count):
    with Progress(  SpinnerColumn(style=Style(color="blue")),TextColumn("{task.description}")) as progress:
        task1=progress.add_task('Getting your subscriptions (this may take awhile)...')
        out=[]
        if constants.OFSCRAPER_RESERVED_LIST in args_.getargs().user_list:
            offsets = range(0, subscribe_count, 10)
            async with sessionbuilder.sessionBuilder() as c: 
                tasks = [scrape_subscriptions(c,offset) for offset in offsets]
                subscriptions = await asyncio.gather(*tasks)
                out.extend(list(chain.from_iterable(subscriptions)))
        progress.remove_task(task1)
        return out







@retry(retry=retry_if_not_exception_type(KeyboardInterrupt),stop=stop_after_attempt(constants.NUM_TRIES),wait=wait_random(min=constants.OF_MIN, max=constants.OF_MAX),reraise=True)   
async def scrape_subscriptions(c,offset=0) -> list:

        async with c.requests( subscriptionsEP.format(offset))() as r:
            if r.ok:
                subscriptions = (await r.json_())["list"]
                log.debug(f"usernames offset {offset}: usernames retrived -> {list(map(lambda x:x.get('username'),subscriptions))}")      
                return subscriptions
            else:
                log.debug(f"[bold]subscriptions response status code:[/bold]{r.status}")
                log.debug(f"[bold]subscriptions response:[/bold] {await r.text_()}")
                log.debug(f"[bold]subscriptions headers:[/bold] {r.headers}")
                r.raise_for_status()
            

def parse_subscriptions(subscriptions: list) -> list:
    datenow=arrow.now()
    data = [
        {"name":profile['username']
         ,"id":profile['id'],
         "sub-price":profile.get("currentSubscribePrice",{}),
         "regular-price":profile.get("subscribedByData").get("regularPrice") if profile.get("subscribedByData") else None,
         "promo-price": sorted(list(filter(lambda x: x.get("canClaim") == True,profile.get("promotions") or [])), key=lambda x: x["price"]),
         "expired":profile.get("subscribedByData").get("expiredAt") if profile.get("subscribedByData") else None,
         "subscribed":(profile.get("subscribedByData").get("subscribes") or [{}])[0].get("startDate") if profile.get("subscribedByData") else None ,
         "renewed":profile.get("subscribedByData").get("renewedAt") if profile.get("subscribedByData") else None,
        "active" :  arrow.get(profile.get("subscribedByData").get("expiredAt"))>datenow if profile.get("subscribedByData") else None


         } for profile in subscriptions]
    data=setpricehelper(data)
    return data

def setpricehelper(data):
    for ele in data:
        prices=list(filter(lambda x:x!=None,[ele.get("sub-price"),(ele.get("promo-price") or [{}])[0].get("price"),ele["regular-price"]]))
        if len(prices)==0:
            ele["price"]=None
        else:
            ele["price"]=min(prices)
    return data
    




