import gradio as gr
import anthropic
import asyncio
import json

thestory=""
last_user_msg = ""

with gr.Blocks() as demo:
    preset={}
    savedata={}#thestory#user_thread#ai_thread#extra_actors#steps#key

    def load_preset():
        global preset
        with open('preset.json', 'r', encoding='utf-8') as f:
            preset = json.load(f)
    
    def load_file():
        global savedata
        try:
            with open('savedata.json', 'r', encoding='utf-8') as f:
                savedata = json.load(f)
        except FileNotFoundError:
            print('savedata does not exist!')        

    def save_file():
        global savedata
        steps = savedata.get('steps',[])
        print("!!!!SAVE FILE!!!!!")
        steps.append([ len(savedata.get('user_thread',[])),len(savedata.get('ai_thread',[])),len(savedata.get('extra_actors',[])) ])
        savedata['steps'] = steps
        with open('savedata.json', 'w',encoding='utf-8') as f:
            json.dump(savedata, f, ensure_ascii=False)    

    load_preset()
    load_file()

    api_tb=gr.Textbox(savedata.get("key",""))
    #到時候記得把api改沒了
    api_tb.label="Claude_api"
    model_options =["claude-v1", "claude-v1-100k", "claude-instant-v1","claude-instant-v1-100k","claude-v1.3", "claude-v1.3-100k", "claude-v1.2","claude-v1.0","claude-instant-v1.1","claude-instant-v1.1-100k","claude-instant-v1.0"]
    model=gr.Dropdown(model_options)
    model.label="模型選擇"
    model.value="claude-v1.3-100k"
    tempeslider=gr.Slider(minimum=0,maximum=1,value=1)
    tempeslider.label="互動的ai溫度"
    #棄用with gr.Row():
    aichat_cb = gr.Chatbot( savedata.get('user_thread',[[None, preset['greeting']]]) )
    aichat_cb.label="對話"
        #棄用aiinput_tb = gr.Textbox()
        #棄用aiinput_tb.label="分析"
        #棄用aiinput_tb.interactive=False
    input_tb = gr.Textbox()
    input_tb.label="用戶輸入"
    button = gr.Button("發送用戶輸入")
    clear = gr.Button("全部清除")
    dl_button = gr.Button("刪除最後一組對話")
    #暫時被讀取劇本取代load_button = gr.Button("讀取")
    loadstory_button = gr.Button("讀取劇本")


    #這個方法是用戶輸入後執行的第一個方法，用來把用戶輸入的東西放進歷史對話欄里面，然後清空用戶對話欄
    def user(user_message, history):
        global last_user_msg
        last_user_msg = user_message
        history = history + [[user_message, ""]]
        savedata['user_thread'] = history
        return "", history
    
    #這個方法是拿來刪除最後一組對話
    def dl(aichat_cb):
        steps = savedata.get("steps",[])
        if(len(steps) > 0):
            steps.pop()
        if len(steps)==0:
            return resetaichat_cb()
        else:
            step = steps[len(steps)-1]
            print(step)
            if(savedata.get('user_thread')):
                savedata['user_thread'] = savedata['user_thread'][:step[0]]
            if(savedata.get('ai_thread')):
                savedata['ai_thread'] = savedata['ai_thread'][:step[1]]
            if(savedata.get('extra_actors')):
                savedata['extra_actors'] = savedata['extra_actors'][:step[2]]
        aichat_cb = savedata['user_thread']
        return aichat_cb
    
    #這個方法是拿來重置（清空）對話欄
    def resetaichat_cb():
        global savedata
        key = savedata.get('key')
        savedata={}
        if(key):
            savedata['key'] = key
        return [[None, preset['greeting']]]

    #這個方法實現了讀取（暫時被讀取劇本取代，需要時才考慮回覆）
    #def load():
        
     #   with open('data.json', 'r') as json_file:
      #      aichat_cb = json.load(json_file)
       # aichat_cb=None
        #aichat_cb=[[None, preset['greeting']]]
        #return aichat_cb
    
    def loadstory():
        load_file()
        aichat_cb=savedata.get('user_thread',[[None, preset['greeting']]])
        return aichat_cb
    
    #這是一個主要用來讓cl自己和自己說話的方法，
    #//它輸入1.用戶的api 2.用戶選擇的模型 3.前置的詞條 4.之前說過的內容。5.溫度控制(可省略)
    #//它輸出1.ai說話
    def cl_analyze(api_input,sl_model,preprompt,temperature=1,maxtoken = 6000):
        c = anthropic.Client(api_key=api_input)
        resp = c.completion(
            prompt=preprompt+f"{anthropic.AI_PROMPT}",
            stop_sequences=[anthropic.HUMAN_PROMPT,"Admin:","Human","人类:"],
            model=sl_model,
            temperature=temperature,
            max_tokens_to_sample=maxtoken,
        )
        return resp["completion"]


    #這個方法用來操控claude和預設內容對話-創作劇本
    def cl_manager_prepare(api_input,sl_model,settemperature=1):
        print("cl經理觸發了!")
        global preset
        global savedata
        results = []
        progress = preset['prepare']
        #aichat_cb.label = "DM商議中!(0/{0})".format(len(progress));
        log = ""
        for i in range(len(progress)):
            obj = progress[i]
            prefix = f"{anthropic.HUMAN_PROMPT}" if (not obj['inject']) else "\n\nAdmin:"
            if(obj['inject'] and i == 0):
                prefix = f"{anthropic.HUMAN_PROMPT}" + prefix
            pre_prompt = prefix + obj['input'].format(last_user_msg)

            log += pre_prompt
            print("\n\n\n>>" + str(i) + ">>" + pre_prompt)
            pre_result=cl_analyze(api_input,obj.get('model',sl_model),log,obj.get('temperature',settemperature),obj.get('max_tokens',6000))
            print("<<<<" + pre_result)
            log += f"{anthropic.AI_PROMPT}" + pre_result        

            results.append(pre_result)

        savedata['ai_thread'] = [preset['start'].format(last_user_msg,pre_result)]
        savedata['thestory'] = pre_result


    #這個方法用來操控claude和預設內容對話-在劇情進行過程中的討論
    def cl_manager_discuss(api_input,sl_model,settemperature=1):
        print("cl經理觸發了!")
        global preset
        global savedata
        results = []
        #如果已經有故事了，就審視當前的遊戲內容，而不是生成劇本
        progress = preset['discuss_progress']
        #aichat_cb.label = "DM商議中!(0/{0})".format(len(progress));
        log = log_to_claude()
        for i in range(len(progress)):
            obj = progress[i]
            prefix = f"{anthropic.HUMAN_PROMPT}" if (not obj['inject']) else "\n\nAdmin:"
            pre_prompt = prefix + obj['input']
            print("\n\n\n>>" + str(i) + ">>" + pre_prompt)
            pre_result=cl_analyze(api_input,obj.get('model',sl_model),log + pre_prompt,obj.get('temperature',settemperature),obj.get('max_tokens',6000))
            print("<<<<" + pre_result)
            results.append(pre_result)

        extra_actors = savedata.get('extra_actors',[])
        extra_actors.append(results[1])
        results[1] = "\n".join(extra_actors)
        thetext_tocl=preset['discuss_end'].format(savedata.get(thestory,""),*results)
        print("<<<<<" + thetext_tocl)
        savedata['ai_thread'].append(thetext_tocl)

        
    def log_to_claude():
        if(not savedata.get('ai_thread')):
            return "\n\nHuman:"
        result = savedata.get('ai_thread')
        text_tocl ="".join(result)
        return text_tocl


    #cl_talk(text_tocl,api_input) 參數1是歷史對話框的值，參數2是用戶的api,參數3是選擇的模型，4是溫度
    #輸出的是一個““會stream最後一句話”的“歷史對話欄””
    async def cl_talk(aichat_cb,api_input,sl_model,settemperature=1):
        #如果現在的對話是第一條，而且劇本是空的（就是並沒有讀取劇本），那就執行cl_manager，進行第一次的dm審議會，生成劇本
        global savedata
        ai_thread = savedata.get('ai_thread',[])
        savedata['key'] = api_input
        print(len(aichat_cb))
        if len(aichat_cb)==2:
            if not savedata.get('thestory'):
                print("現在是第一條內容,即將開始dm審議會，並生成劇本")
                cl_manager_prepare(api_input,sl_model,settemperature)
        elif len(aichat_cb)%preset['discuss_gap']==2:
                print("現在是每5條內容中的第一條,即將開始第二輪的claude審議會")
                cl_manager_discuss(api_input,sl_model,settemperature)
                ai_thread.append("\n\nHuman" + last_user_msg)
                savedata['ai_thread'] = ai_thread
        else:
            ai_thread.append("\n\nHuman" + last_user_msg)
            savedata['ai_thread'] = ai_thread


        thetext_tocl = log_to_claude()
        c = anthropic.Client(api_key=api_input)
        response = await c.acompletion_stream(
        prompt=f"{anthropic.HUMAN_PROMPT}"+thetext_tocl+f"{anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT,"Admin:","Human","人类:"],
        temperature=settemperature,
        max_tokens_to_sample=6000,
        model=sl_model,
        stream=True,        
    )

        async for data in response:
            aichat_cb[-1][1] =data["completion"]
            if data['stop_reason']=='stop_sequence' or data['stop_reason'] == "max_tokens":
                ai_thread = savedata.get('ai_thread',[])
                ai_thread.append(f"{anthropic.AI_PROMPT}" + data['completion'])
                savedata['ai_thread'] = ai_thread
                savedata['user_thread'] = aichat_cb
                save_file()
            yield aichat_cb

    button.click(user,[input_tb,aichat_cb],[input_tb,aichat_cb]).then(cl_talk,[aichat_cb,api_tb,model,tempeslider],aichat_cb)
    input_tb.submit(user,[input_tb,aichat_cb],[input_tb,aichat_cb]).then(cl_talk,[aichat_cb,api_tb,model,tempeslider],aichat_cb)
    #這里是按enter或發送用戶輸入後會連續觸發兩個方法
    #第一個是user方法，用來把用戶輸入的東西放進對話欄(同時也是歷史對話)里面，然後清空用戶對話欄。
    #第二個是cl_talk方法，傳遞進去了[1.ai的對話欄,這是一個list,里面會記入歷史對話2.用戶輸入的api。]
    #輸出的是歷史對話欄，他會加入claude回覆的字典中的["completion"]的值
    clear.click(resetaichat_cb, None, aichat_cb, queue=False)
    #這個鍵會清空歷史對話欄
    dl_button.click(dl,aichat_cb,aichat_cb, queue=False)
    #這個鍵會刪除最後一個ai和用戶的對話

    #load_button.click(load,None,aichat_cb, queue=False)    
    #（暫時被讀取劇本取代）這個鍵會讓歷史對話欄恢覆成上次保存的所有對話內容

    loadstory_button.click(loadstory,None,aichat_cb, queue=False).then(user,[input_tb,aichat_cb]).then(cl_talk,[aichat_cb,api_tb,model,tempeslider],aichat_cb)
    #讀取目標位置的劇本
    

demo.title="Claude storywriter Webui"    
demo.queue()
if __name__ == "__main__":
    demo.launch()