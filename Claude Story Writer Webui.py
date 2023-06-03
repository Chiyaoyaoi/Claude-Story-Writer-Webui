import gradio as gr
import os
import random
import anthropic
import copy
import time
import asyncio
import json
thestory=""
thetext_tocl = ""
last_user_msg = ""

with gr.Blocks() as demo:
    preset={}
    def load_preset():
        global preset
        with open('preset.json', 'r',encoding='utf-8') as f:
            preset = json.load(f)
    
    load_preset()

    api_tb=gr.Textbox("")
    #到時候記得把api改沒了
    api_tb.label="Claude_api"
    model_options =["claude-v1", "claude-v1-100k", "claude-instant-v1","claude-instant-v1-100k","claude-v1.3", "claude-v1.3-100k", "claude-v1.2","claude-v1.0","claude-instant-v1.1","claude-instant-v1.1-100k","claude-instant-v1.0"]
    model=gr.Dropdown(model_options)
    model.label="模型選擇"
    model.value="claude-v1.3-100k"
    tempeslider=gr.Slider(minimum=0,maximum=1,value=1)
    tempeslider.label="互動的ai溫度"
    #棄用with gr.Row():
    aichat_cb = gr.Chatbot([[None, preset['greeting']]])
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
        return "", history + [[user_message, ""]]
    
    #這個方法是拿來刪除最後一組對話
    def dl(aichat_cb):
        aichat_cb.pop()    
        if len(aichat_cb)==0:
            aichat_cb.append([None, preset['greeting']])
        return aichat_cb
    
    #這個方法是拿來重置（清空）對話欄
    def resetaichat_cb():
        global thestory
        thestory=""
        return [[None, preset['greeting']]]

    #這個方法實現了讀取（暫時被讀取劇本取代，需要時才考慮回覆）
    #def load():
        
     #   with open('data.json', 'r') as json_file:
      #      aichat_cb = json.load(json_file)
       # aichat_cb=None
        #aichat_cb=[[None, preset['greeting']]]
        #return aichat_cb
    
    def loadstory():
        global thestory
        global thetext_tocl
        with open('abbreviated_story.json', 'r',encoding='utf-8') as json_file:
            thestory = json.load(json_file)
        aichat_cb=None
        aichat_cb=[[None, "你載入了一個劇本，現在我將生成內容："],[None,""]]
        thetext_tocl=preset['start'].format(last_user_msg,thestory)
        return aichat_cb
    
    #這是一個主要用來讓cl自己和自己說話的方法，
    #//它輸入1.用戶的api 2.用戶選擇的模型 3.前置的詞條 4.之前說過的內容。5.溫度控制(可省略)
    #//它輸出1.ai說話
    def cl_analyze(api_input,sl_model,preprompt,temperature=1,maxtoken = 6000):
        c = anthropic.Client(api_key=api_input)
        resp = c.completion(
            prompt=preprompt+f"{anthropic.AI_PROMPT}",
            stop_sequences=[anthropic.HUMAN_PROMPT,"Admin:"],
            model=sl_model,
            temperature=temperature,
            max_tokens_to_sample=maxtoken,
        )
        return resp["completion"]


    #這個方法用來操控claude和預設內容對話
    def cl_manager(api_input,sl_model,history,settemperature=1):
        print("cl經理觸發了!")
        global preset
        global thestory
        results = []
        DMs=[]
        #如果已經有故事了，就審視當前的遊戲內容，而不是生成劇本
        if thestory=="":
            prepare = preset['prepare']
        else:
            prepare = preset['prepare2']
        #aichat_cb.label = "DM商議中!(0/{0})".format(len(prepare));
        log = ""
        for i in range(len(prepare)):
            obj = prepare[i]
            prefix = f"{anthropic.HUMAN_PROMPT}" if (not obj['inject']) else "\n\nAdmin:"
            if(obj['inject'] and i == 0):
                prefix = f"{anthropic.HUMAN_PROMPT}" + prefix
            pre_prompt = prefix + obj['input'].format(last_user_msg,thestory)
            
            #如果dm會議是第二次以上
            if prepare ==preset['prepare2']:
                log += pre_prompt
                print(">>" + str(i) + ">>" + pre_prompt)
                pre_result=cl_analyze(api_input,obj.get('model',sl_model),log,obj.get('temperature',settemperature),obj.get('max_tokens',6000))
                print("<<<<" + pre_result)
                log += f"{anthropic.AI_PROMPT}" + pre_result

                DMs.append(pre_result)
                with open('data_of_story.json', 'w',encoding='utf-8') as json_file:
                    json.dump(DMs, json_file,ensure_ascii=False)
            else:
                log += pre_prompt
                print(">>" + str(i) + ">>" + pre_prompt)
                pre_result=cl_analyze(api_input,obj.get('model',sl_model),log,obj.get('temperature',settemperature),obj.get('max_tokens',6000))
                print("<<<<" + pre_result)
                log += f"{anthropic.AI_PROMPT}" + pre_result


            results.append(pre_result)

        global thetext_tocl
        #thetext_tocl是簡寫內容後把東西丟給cl_talk方法
        #如果是第二輪以上的dm會議的話,執行的是start2，不然是start
        if prepare ==preset['prepare2']:
            #with open('data_of_story.json', 'r',encoding='utf-8') as f:
                #DMs = json.load(f)
            thetext_tocl=preset['start2'].format(thetext_tocl,thestory,DMs[0],DMs[1],DMs[2],DMs[3],DMs[4])
        else:
            with open('abbreviated_story.json', 'w',encoding='utf-8') as json_file:
                json.dump(pre_result, json_file,ensure_ascii=False)
            thestory=pre_result
            thetext_tocl=preset['start'].format(last_user_msg,pre_result)
        


    def trans_chattoclaude(aichat_cb):
        result = copy.deepcopy(aichat_cb)
        #把aichat_cb先覆制成result，然後切換成claude看得懂的格式,不去動aichat_cb是因為，他還需要給chatbot看
        for index, b in enumerate(result):
            if index == 0:
                b[0] = ""
                b[1] = ""
                continue
            if b[0] != None:
                b[0] = "\n\nHuman:"+b[0]
            if b[1] != None:
                b[1] = "\n\nAssistant:" + b[1]
        text_tocl ="".join([str(item) for sublist in result for item in sublist if item is not None])
        #這里的text_tocl就是給claude看的
        global thetext_tocl 
        thetext_tocl= text_tocl



    #cl_talk(text_tocl,api_input) 參數1是歷史對話框的值，參數2是用戶的api,參數3是選擇的模型，4是溫度
    #輸出的是一個““會stream最後一句話”的“歷史對話欄””
    async def cl_talk(aichat_cb,api_input,sl_model,settemperature=1):
        global thetext_tocl
        #如果現在的對話是第一條，而且劇本是空的（就是並沒有讀取劇本），那就執行cl_manager，進行第一次的dm審議會，生成劇本
        print(len(aichat_cb))
        if len(aichat_cb)==2:
            if thestory=="":
                print("現在是第一條內容,即將開始dm審議會，並生成劇本")
                cl_manager(api_input,sl_model,thetext_tocl,settemperature)
        else:
            if len(aichat_cb)%5==2:
                print("現在是每5條內容中的第一條,即將開始第二輪的claude審議會")
                cl_manager(api_input,sl_model,thetext_tocl,settemperature)
        c = anthropic.Client(api_key=api_input)

        print("-------")
        print(thetext_tocl)
        print(settemperature)
        print(sl_model)
        print("-------")

        response = await c.acompletion_stream(
        prompt=f"{anthropic.HUMAN_PROMPT}"+thetext_tocl+f"{anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT,"Admin:"],
        temperature=settemperature,
        max_tokens_to_sample=6000,
        model=sl_model,
        stream=True,        
    )

        async for data in response:
            aichat_cb[-1][1] =data["completion"]
            if data['stop_reason']=='stop_sequence':
                with open('data.json', 'w',encoding='utf-8') as json_file:
                    json.dump(aichat_cb, json_file,ensure_ascii=False)
            yield aichat_cb

    button.click(user,[input_tb,aichat_cb],[input_tb,aichat_cb]).then(trans_chattoclaude,aichat_cb,None).then(cl_talk,[aichat_cb,api_tb,model,tempeslider],aichat_cb)
    input_tb.submit(user,[input_tb,aichat_cb],[input_tb,aichat_cb]).then(trans_chattoclaude,aichat_cb,None).then(cl_talk,[aichat_cb,api_tb,model,tempeslider],aichat_cb)
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