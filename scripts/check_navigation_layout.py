"""Optional local Firefox layout check; never submits a search.

Start Streamlit on 127.0.0.1:8510 and an isolated headless Firefox with
--remote-debugging-port 9231, then run with the project venv (websockets required).
See docs/readiness/navigation-layout/README.md. Not part of offline pytest.
"""
import asyncio
import base64
import json
from pathlib import Path

from websockets.asyncio.client import connect

OUTPUT = Path('docs/readiness/navigation-layout')
OUTPUT.mkdir(parents=True, exist_ok=True)


async def main():
    async with connect('ws://127.0.0.1:9231/session') as ws:
        sequence = 0

        async def command(method, params):
            nonlocal sequence
            sequence += 1
            await ws.send(json.dumps({'id': sequence, 'method': method, 'params': params}))
            while True:
                reply = json.loads(await asyncio.wait_for(ws.recv(), 20))
                if reply.get('id') == sequence:
                    if reply.get('type') == 'error':
                        raise RuntimeError(reply)
                    return reply['result']

        await command('session.new', {'capabilities': {}})
        try:
            tree = await command('browsingContext.getTree', {})
            context = tree['contexts'][0]['context']

            async def evaluate(expression):
                reply = await command('script.evaluate', {'expression': expression, 'target': {'context': context}, 'awaitPromise': True})
                if reply['type'] != 'success':
                    raise RuntimeError(reply)
                return reply['result'].get('value')

            async def wait_for(expression):
                async with asyncio.timeout(20):
                    while not await evaluate(expression):
                        await asyncio.sleep(.1)

            expression = '''JSON.stringify((() => {
                const rect = e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}; };
                const brand=document.querySelector('.st-key-relink_brand');
                return {viewport:innerWidth,brand:rect(brand),brandPosition:getComputedStyle(brand).position,
                    oldTabLists:document.querySelectorAll('[data-baseweb="tab-list"]').length,
                    tablist:rect(document.querySelector('[role="tablist"]')),
                    tabs:[...document.querySelectorAll('[role="tab"]')].map(e=>({label:e.textContent,id:e.id,rect:rect(e)})),
                    overflow:document.documentElement.scrollWidth>innerWidth};
            })())'''
            checks = []
            for width in (1688, 1024, 768, 640, 390, 320):
                await command('browsingContext.setViewport', {'context': context, 'viewport': {'width': width, 'height': 1000}, 'devicePixelRatio': 1})
                await command('browsingContext.navigate', {'context': context, 'url': 'http://127.0.0.1:8510/', 'wait': 'complete'})
                await wait_for('document.querySelectorAll("[role=tab]").length === 3 && !!document.querySelector(".st-key-dataset_input_panel input") && getComputedStyle(document.querySelector(".stApp")).getPropertyValue("--rl-amber").trim() === "#ffc17a"')
                await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                result = json.loads(await evaluate(expression))
                screenshot = await command('browsingContext.captureScreenshot', {'context': context})
                (OUTPUT / f'{width}.png').write_bytes(base64.b64decode(screenshot['data']))
                checks.append(result)
                (OUTPUT / 'measurements.json').write_text(json.dumps(checks, indent=2)+'\n')
                assert len(result['tabs']) == 3
                assert not result['overflow'], f'Page overflow at {width}'
                assert result['brandPosition'] == 'static', result
                b = result['brand']
                for t in result['tabs']:
                    r = t['rect']
                    assert b['right'] <= r['x'] or r['right'] <= b['x'] or b['bottom'] <= r['y'] or r['bottom'] <= b['y'], f"Brand overlaps {t['label']} at {width}"
                print(f'PASS {width}px: brand and all three tabs do not overlap; no page overflow', flush=True)

            await command('browsingContext.setViewport', {'context': context, 'viewport': {'width': 390, 'height': 1000}, 'devicePixelRatio': 1})
            await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            # Use actual observed tab IDs and pointer clicks; no search is submitted.
            for tab in result['tabs']:
                point = json.loads(await evaluate(f'JSON.stringify((() => {{const r=document.getElementById({json.dumps(tab["id"])}).getBoundingClientRect(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}};}})())'))
                await command('input.performActions', {'context': context, 'actions': [{'type': 'pointer', 'id': 'mouse', 'parameters': {'pointerType': 'mouse'}, 'actions': [{'type': 'pointerMove', 'x': point['x'], 'y': point['y']}, {'type': 'pointerDown', 'button': 0}, {'type': 'pointerUp', 'button': 0}]}]})
                await wait_for(f'document.getElementById({json.dumps(tab["id"])}).getAttribute("aria-selected") === "true"')
                visible = await evaluate('document.querySelector("[role=tabpanel]:not([hidden]) h3, [role=tabpanel]:not([hidden]) h2")?.textContent')
                assert visible and tab['label'].lower() in visible.lower(), (tab['label'], visible)
                print(f'PASS tab activation: {tab["label"]}', flush=True)

            await evaluate('document.querySelectorAll("style").forEach(e => { if(e.textContent.includes("--rl-amber:")) e.remove(); })')
            result = json.loads(await evaluate(expression))
            assert result['brandPosition'] == 'static'
            assert result['brand']['bottom'] <= result['tablist']['y']
            print('PASS missing custom CSS: brand remains above native tabs', flush=True)
        finally:
            await command('session.end', {})


if __name__ == '__main__':
    asyncio.run(main())
