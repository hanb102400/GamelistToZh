import os
import sys
import argparse
import hashlib
import csv
import xml.etree.ElementTree as ET
import requests
import json
import re
import time
import timeit

def contains_chinese(text):
    """检查字符串是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def calculate_md5(text):
    """计算字符串的MD5哈希值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

# 修复：将字符串中的换行符替换为转义形式 \n
def fix_json(text):
    # 匹配双引号内的内容并替换换行符
    import re
    return re.sub(
        r'"(.*?)"', 
        lambda m: '"' + m.group(1).replace('\n', '\\n') + '"',
        text,
        flags=re.DOTALL
    )
    
def translate_content(ai_type, api_key, model, name, desc):
    """
    使用指定的AI模型翻译游戏名称和描述
    返回格式: {"name_zh": "中文名称", "desc_zh": "中文描述"}
    """
    # 验证AI类型是否支持
    supported_ai = ['deepseek', 'doubao', 'qianwen', 'xinghuo', 'hunyuan', 'kimi']
    if ai_type not in supported_ai:
        print(f"错误: 不支持的AI类型 '{ai_type}'，支持的AI类型: {', '.join(supported_ai)}")
        return None
    
    # 系统提示词（根据您的要求）
    system_prompt = (
        "你是一位专业的复古模拟游戏本地化翻译家，负责将游戏名称和描述翻译成简体中文。\n"
        "请遵守以下规则：\n"
        "1. 游戏名称优先使用中文官方译名或中文常用译名\n"
        "2. 游戏名称翻译后不要有《》书名号\n"
        "3. 游戏描述要流畅自然，保持原有段落结构\n"
        "4. 保留所有特殊符号和格式（如换行符、引号等）\n"
        "5. 技术术语（如游戏类型、机制）要准确翻译\n"
        "6. 游戏名称含义不明和翻译信息不足的返回空文本\n"
        "7. 返回结果必须是严格的JSON格式: {\"name_zh\": \"中文名称\", \"desc_zh\": \"中文描述\"}"
    )
    
    # 用户请求内容
    user_content = f"请翻译以下内容：游戏名称：{name}\n\n游戏描述：{desc}"
    
    # 构建请求负载
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}  # 要求API返回JSON格式
    }
    
    # DeepSeek API配置
    if ai_type == "deepseek":
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model
    
    # doubao API配置
    elif ai_type == "doubao":
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model
        
    # qianwen API配置
    elif ai_type == "qianwen":
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model
    
    # xinghuo API配置
    elif ai_type == "xinghuo":
        url = "https://spark-api-open.xf-yun.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model
    
     # hunyuan API配置
    elif ai_type == "hunyuan":
        url = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model
        
    # kimi API配置
    elif ai_type == "kimi":
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload["model"] = model    
     
    max_retries = 3
    retry_delay = 1  # 初始延迟1秒
    
    for attempt in range(max_retries):
        try:
            # 发送API请求
            start_time = timeit.default_timer()
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            
            # 检查HTTP错误状态码
            if response.status_code >= 500:
                raise Exception(f"服务器错误 ({response.status_code})")
            elif response.status_code == 429:
                raise Exception("速率限制 (429 Too Many Requests)")
            elif response.status_code >= 400:
                raise Exception(f"客户端错误 ({response.status_code})")
                
            response.raise_for_status()
            response_data = response.json()
            elapsed = timeit.default_timer() - start_time
            
            # 提取翻译结果
            translated_text = None
            
            # 尝试从标准位置获取内容
            if 'choices' in response_data and len(response_data['choices']) > 0:
                choice = response_data['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    translated_text = choice['message']['content']

            # 如果标准位置没有找到，尝试其他可能的位置
            if not translated_text:
                # 尝试获取第一个非空内容
                for key in ['content', 'text', 'result', 'output']:
                    if key in response_data:
                        translated_text = response_data[key]
                        break
            
            if not translated_text:
                print(f"无法从API响应中找到翻译内容")
                return None, elapsed
            
            # 尝试解析JSON
            try:
                result = json.loads(translated_text)
            except json.JSONDecodeError:
                try:
                    # 如果不是JSON，尝试手动提取
                    fixed_text = fix_json(translated_text)
                    result = json.loads(fixed_text)  # 成功解析
                    if 'name_zh' in result and 'desc_zh' in result:
                        return result, elapsed
                    elif 'name_zh' in result:  # 只有名称的情况
                        return {"name_zh": result['name_zh'], "desc_zh": desc}, elapsed
                except json.JSONDecodeError:
                    print(f"解析JSON失败，尝试文本匹配: {translated_text}")
                    pass
                
            # 手动提取名称和描述
            name_match = re.search(r'(?:"name_zh"\s*:\s*")(.*?)(?:"|$)', translated_text)
            desc_match = re.search(r'(?:"desc_zh"\s*:\s*")(.*?)(?:"|$)', translated_text)
            
            if not name_match or not desc_match:
                # 尝试更宽松的匹配
                name_match = re.search(r'(?:名称[：:]\s*)(.*?)(?:\n|$)', translated_text, re.IGNORECASE)
                desc_match = re.search(r'(?:描述[：:]\s*)([\s\S]*)', translated_text, re.IGNORECASE)
            
            if name_match and desc_match:
                return {
                    "name_zh": name_match.group(1).strip(),
                    "desc_zh": desc_match.group(1).strip()
                }, elapsed
            elif name_match:  # 只有名称匹配到
                return {
                    "name_zh": name_match.group(1).strip(),
                    "desc_zh": desc
                }, elapsed
            
            print(f"无法解析API返回的内容: {translated_text[:200]}...")
            return None, elapsed
            
        except Exception as e:
            elapsed = timeit.default_timer() - start_time if 'start_time' in locals() else 0
            error_msg = str(e)

            # 特殊处理速率限制错误
            if "429" in error_msg:
                # 尝试从响应头获取重试时间
                retry_after = response.headers.get('Retry-After', None)
                if retry_after:
                    try:
                        retry_delay = int(retry_after) + 1
                    except ValueError:
                        pass
            
            print(f"{ai_type} API调用失败 (尝试 {attempt+1}/{max_retries}): {error_msg}")
            
            # 最后一次尝试失败后返回错误
            if attempt == max_retries - 1:
                print(f"{ai_type} API调用失败，已达最大重试次数")
                return None, elapsed
            
            # 指数退避策略
            print(f"{retry_delay}秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 10  # 每次失败后延迟时间加倍
    
    return None, 0

def load_database_cache(script_dir):
    """从database目录加载所有CSV缓存文件，使用游戏名称作为键"""
    cache = {}
    db_dir = os.path.join(script_dir, 'database')
    
    if not os.path.exists(db_dir):
        return cache
    
    for filename in os.listdir(db_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(db_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # 使用game_id作为键
                        game_id = calculate_md5(row['NAME'].strip())
                        cache[game_id] = {
 							'file': row.get('FILE', ''),  
                            'name': row['NAME'],
                            'name_zh': row['NAME_ZH'],
                            'desc': row['DESC'],
                            'desc_zh': row['DESC_ZH']
                        }
            except Exception as e:
                print(f"加载缓存文件{filename}出错: {str(e)}")
    return cache

def truncate_text(text, max_length=200):
    """截断文本并添加省略号（如果需要）"""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def get_filename_from_path(path):
    """从路径中提取文件名（带后缀）"""
    if not path:
        return "[无路径]"
    
    # 如果路径是URL，提取最后一部分作为文件名
    if path.startswith(('http://', 'https://')):
        return path.split('/')[-1]
    
    # 如果是文件路径，使用os.path.basename
    return os.path.basename(path)

def sort_games_by_path(root):
    """按照path标签对游戏列表进行排序"""
    # 获取所有game元素
    games = root.findall('game')
    
    # 移除所有game元素
    for game in games:
        root.remove(game)
    
    # 按path标签内容排序
    games_sorted = sorted(games, key=lambda game: game.find('path').text)
    
    # 重新添加排序后的游戏
    for game in games_sorted:
        root.append(game)

def main():
    parser = argparse.ArgumentParser(description='游戏列表翻译工具')
    parser.add_argument('--input', required=True, help='gamelist.xml文件路径')
    parser.add_argument('--ai', required=True, choices=['deepseek','doubao','qianwen','xinghuo','hunyuan','kimi'], 
                        help='AI翻译引擎')
    parser.add_argument('--api_key', required=True, help='AI API密钥')
    parser.add_argument('--model', required=True, help='AI模型名称')
    parser.add_argument('--local_db', action='store_true', help='是否使用本地数据库缓存')
    
    args = parser.parse_args()
    print(f"使用AI大语言模型：{args.ai}-{args.model}")
     
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载本地数据库缓存
    database_cache = {}
    if args.local_db:
        database_cache = load_database_cache(script_dir)
        print(f"已加载 {len(database_cache)} 条本地缓存记录")
    
    # 解析XML文件
    try:
        tree = ET.parse(args.input)
        root = tree.getroot()
    except Exception as e:
        print(f"解析XML文件失败: {str(e)}")
        sys.exit(1)
    
    # 准备缓存文件路径
    xml_dir = os.path.dirname(os.path.abspath(args.input))
    cache_file = os.path.join(xml_dir, 'gamelist_zh.cache')
    processed_ids = set()
    processed_raws = {}
    
    # 创建或打开缓存文件
    cache_file_exists = os.path.exists(cache_file)
    cache_file_handle = open(cache_file, 'a', encoding='utf-8', newline='')
    
    # 字段列表
    fieldnames = ['ID', 'FILE', 'NAME', 'NAME_ZH', 'DESC', 'DESC_ZH']
    cache_writer = csv.DictWriter(cache_file_handle, fieldnames=fieldnames)
    
    # 如果文件不存在或为空，写入标题
    if not cache_file_exists or os.stat(cache_file).st_size == 0:
        cache_writer.writeheader()
        cache_file_handle.flush()
    
    # 加载已有缓存
    if cache_file_exists:
        with open(cache_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_ids.add(row['ID'])
                processed_raws[row['ID']]=row
    
    # 遍历所有game节点
    success_count = 0
    total_games = 0
    processed_games = 0
    total_translation_time = 0.0
    
    # 记录整体开始时间
    overall_start_time = timeit.default_timer()
    
    # 先计算游戏总数
    for game in root.findall('game'):
        total_games += 1
    
    # 重置计数器
    current_game = 0
    
    for game in root.findall('game'):
        current_game += 1
        name_elem = game.find('name')
        desc_elem = game.find('desc')
        path_elem = game.find('path')
        
        # 获取路径文件名用于显示
        path_text = path_elem.text if path_elem is not None else ""
        file_name = get_filename_from_path(path_text)
        
        # 跳过没有name的游戏
        if name_elem is None or name_elem.text is None:
            print(f"[{current_game}/{total_games}] 忽略无名称游戏: {file_name}")
            continue
            
        name_text = name_elem.text.strip()
        desc_text = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
        
        # 跳过包含中文的游戏
        if contains_chinese(name_text):
            print(f"[{current_game}/{total_games}] 忽略包含中文的游戏: {name_text}")
            continue
            
        # 计算唯一ID
        game_id = calculate_md5(name_text)
        
        # 跳过已处理的游戏
        if game_id in processed_ids:
            # 读取缓存写入
            cache_row = processed_raws[game_id]
            name_zh = cache_row['NAME_ZH']
            desc_zh = cache_row['DESC_ZH']
            print(f"\n[{current_game}/{total_games}] 加载历史翻译: {name_text} -> {name_zh}")
            translation_time = 0.0
            
            # 更新XML节点
            name_elem.text = name_zh
            if desc_elem is not None:
                desc_elem.text = desc_zh
            continue
            
        # 检查本地缓存
        game_id = calculate_md5(name_text.strip())
        if args.local_db and game_id in database_cache:
            cache_entry = database_cache[game_id]
            name_zh = cache_entry['name_zh']
            desc_zh = cache_entry['desc_zh']
            print(f"\n[{current_game}/{total_games}] 使用本地数据库翻译: {name_text}")
            print(f"游戏名称: {name_text} ")
            print(f"游戏描述: {truncate_text(desc_text)}")
            print(f"翻译名称: {name_zh}")
            print(f"翻译描述: {truncate_text(desc_zh)}")
            translation_time = 0.0
        else:
            # 调用AI翻译
            print(f"\n[{current_game}/{total_games}] 正在翻译: {file_name}")
            start_time = timeit.default_timer()
            result = translate_content(args.ai, args.api_key, args.model, name_text, desc_text)
            translation_time = timeit.default_timer() - start_time
            
            if not result:
                print(f"翻译失败: {name_text}")
                continue
                
            result_data, api_time = result
            if not result_data:
                print(f"翻译失败: {name_text}")
                continue
            name_zh = result_data.get('name_zh', name_text)  # 确保有名称
            desc_zh = result_data.get('desc_zh', desc_text)  # 确保有描述
            
            # 转换特殊字符
            desc_zh = desc_zh.replace(r'\n', '\n')
            
            if name_zh is None or len(name_zh) == 0:
                print(f"信息不足，翻译失败")
                continue
            
            # 验证翻译结果
            if name_zh == name_text and desc_zh == desc_text:
                print(f"翻译可能未成功: {name_text} -> {name_zh}")
                continue
            
            print(f"游戏名称: {name_text} ")
            print(f"游戏描述: {truncate_text(desc_text)}")
            print(f"翻译名称: {name_zh}")
            print(f"翻译描述: {truncate_text(desc_zh)}")
            print(f"翻译耗时: {translation_time:.2f}秒")
            
            # 添加API延迟避免速率限制
            time.sleep(0.1)
        
        # 更新XML节点
        name_elem.text = name_zh
        if desc_elem is not None:
            desc_elem.text = desc_zh
        
        # 立即写入缓存文件
        cache_record = {
            'ID': game_id,
            'FILE': file_name,  # 添加FILE字段
            'NAME': name_text,
            'NAME_ZH': name_zh,
            'DESC': desc_text,
            'DESC_ZH': desc_zh
        }
        cache_writer.writerow(cache_record)
        cache_file_handle.flush()  # 确保立即写入磁盘
        processed_ids.add(game_id)
        processed_raws[game_id]=cache_record
        
        success_count += 1
        processed_games += 1
        total_translation_time += translation_time
        
        # 报告当前进度
        print(f"[{current_game}/{total_games}] 已成功翻译 {success_count} 个游戏")
    
    # 关闭缓存文件
    cache_file_handle.close()
    
    # 计算总耗时
    overall_time = timeit.default_timer() - overall_start_time
    
    # 检查翻译结果
    if success_count == 0:
        print("\n没有游戏被翻译，退出程序")
        sys.exit(1)
    
    # 按照path标签对游戏列表排序
    sort_games_by_path(root)
    print("已按照path标签对游戏列表进行排序")
    
    # 保存翻译后的XML
    output_file = os.path.join(xml_dir, 'gamelist_zh.xml')
    try:
        # 保持原始XML声明
        with open(output_file, 'wb') as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            tree.write(f, encoding='utf-8')
        print(f"已生成翻译文件: {output_file}")
    except Exception as e:
        print(f"保存翻译文件失败: {str(e)}")
        sys.exit(1)
    
    # 备份原始文件
    origin_file = os.path.join(xml_dir, 'gamelist_origin.xml')
    input_file = os.path.abspath(args.input)
    
    try:
        # 如果原始备份已存在，直接删除当前文件
        if os.path.exists(origin_file):
            os.remove(input_file)
        else:
            os.rename(input_file, origin_file)
        
        # 复制翻译文件为原始文件名
        os.replace(output_file, input_file)
        print(f"已备份原始文件并替换为新翻译文件")
    except Exception as e:
        print(f"文件备份失败: {str(e)}")
        sys.exit(1)
    
    # 处理缓存文件
    try:
        if args.local_db:
            # 获取目录名作为数据库文件名
            dir_name = os.path.basename(xml_dir)
            db_file = os.path.join(script_dir, 'database', f"{dir_name}.csv")
            
            # 创建database目录
            db_dir = os.path.join(script_dir, 'database')
            os.makedirs(db_dir, exist_ok=True)
            
            # 复制缓存内容到数据库
            if os.path.exists(cache_file) and success_count > 0:
                if not os.path.exists(db_file):
                    os.rename(cache_file, db_file)
                    print(f"已保存数据库缓存: {db_file}")
                else:
                    print(f"数据库缓存已存在: {db_file}")
        else:
            # 直接删除缓存文件
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print("已删除临时缓存文件")
    except Exception as e:
        print(f"缓存处理失败: {str(e)}")
    
    # 打印最终统计信息
    avg_time_per_game = total_translation_time / success_count if success_count > 0 else 0
    
    print("\n" + "="*50)
    print("翻译完成!")
    print(f"游戏总数: {total_games}")
    print(f"成功翻译: {success_count} 个游戏")
    print(f"跳过: {total_games - success_count} 个游戏")
    print(f"总耗时: {overall_time:.2f}秒")
    print(f"翻译总耗时: {total_translation_time:.2f}秒")
    print(f"平均每游戏翻译时间: {avg_time_per_game:.2f}秒")
    print(f"共保存 {success_count} 条缓存记录")
    print("="*50)

if __name__ == '__main__':
    main()
