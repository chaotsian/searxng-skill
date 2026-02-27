import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, urlparse, parse_qs
import json
import logging

logger = logging.getLogger(__name__)

class SearxNGSearchSkill:
    """SearXNG搜索技能实现"""
    
    def __init__(self, base_url: str = "http://soudb.cn:4000"):
        """
        初始化SearXNG客户端
        Args:
            base_url: SearXNG实例地址，默认为本地4000端口
        """
        self.base_url = base_url
        self.search_endpoint = f"{base_url}/search"
        
    async def search(
        self,
        query: str,
        limit: int = 10,
        language: str = "all",
        time_range: Optional[str] = None,
        categories: List[str] = ["general"],
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        执行SearXNG搜索
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量
            language: 语言过滤
            time_range: 时间范围 (day/week/month/year)
            categories: 搜索类别
            format: 返回格式 (json/csv/rss)
            
        Returns:
            搜索结果字典
        """
        # 构建请求参数
        params = {
            "q": query,
            "format": format,
            "categories": ",".join(categories) if categories else "general"
        }
        
        if language != "all":
            params["language"] = language
            
        if time_range:
            params["time_range"] = time_range
            
        # 添加安全搜索
        params["safesearch"] = "0"  # 0=关闭,1=中等,2=严格
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.search_endpoint,
                    params=params,
                    headers={
                        "User-Agent": "OpenClaw-SearXNG-Skill/1.0"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"SearXNG返回错误: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"搜索服务返回错误: {response.status}",
                            "results": []
                        }
                    
                    # 解析JSON响应
                    data = await response.json()
                    
                    # 处理结果
                    results = []
                    for item in data.get("results", [])[:limit]:
                        result = {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "engine": item.get("engine", ""),
                            "score": item.get("score", 0),
                            "publishedDate": item.get("publishedDate", "")
                        }
                        results.append(result)
                    
                    # 获取建议词
                    suggestions = data.get("suggestions", [])
                    
                    # 获取未过滤结果数
                    number_of_results = data.get("number_of_results", 0)
                    
                    return {
                        "success": True,
                        "query": query,
                        "total_results": number_of_results,
                        "returned_count": len(results),
                        "results": results,
                        "suggestions": suggestions,
                        "search_url": str(response.url)
                    }
                    
        except asyncio.TimeoutError:
            logger.error("SearXNG请求超时")
            return {
                "success": False,
                "error": "搜索请求超时",
                "results": []
            }
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {str(e)}")
            return {
                "success": False,
                "error": f"网络连接失败: {str(e)}",
                "results": []
            }
        except json.JSONDecodeError as e:
            logger.error(f"解析响应失败: {str(e)}")
            return {
                "success": False,
                "error": "搜索结果解析失败",
                "results": []
            }
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}",
                "results": []
            }
    
    async def search_advanced(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        高级搜索，支持更多SearXNG特性
        
        支持的额外参数:
            - pageno: 页码
            - category: 类别
            - time_range: 时间范围
            - safesearch: 安全搜索级别
            - format: 输出格式
        """
        return await self.search(query, **kwargs)


# OpenClaw技能入口函数
async def searxng_search(
    query: str,
    limit: int = 10,
    language: str = "all",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    searxng_url: Optional[str] = None,
    ctx=None
) -> str:
    """
    OpenClaw技能入口 - SearXNG搜索
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量
        language: 语言代码
        time_range: 时间范围
        categories: 搜索类别
        searxng_url: 自定义SearXNG地址
        ctx: OpenClaw上下文
        
    Returns:
        格式化的搜索结果文本
    """
    # 获取配置
    config = ctx.get("config", {}) if ctx else {}
    base_url = searxng_url or config.get("searxng_base_url", "http://soudb.cn:4000")
    
    # 初始化搜索器
    searcher = SearxNGSearchSkill(base_url=base_url)
    
    # 设置默认类别
    if categories is None:
        categories = ["general"]
    
    # 执行搜索
    result = await searcher.search(
        query=query,
        limit=limit,
        language=language,
        time_range=time_range,
        categories=categories
    )
    
    # 格式化输出
    if not result["success"]:
        return f"❌ 搜索失败: {result.get('error', '未知错误')}"
    
    if not result["results"]:
        return f"🔍 未找到关于「{query}」的搜索结果"
    
    # 构建返回消息
    output = []
    output.append(f"🔍 **搜索关键词**: {result['query']}")
    
    if result.get("total_results"):
        output.append(f"📊 **找到约 {result['total_results']} 条结果** (显示前{result['returned_count']}条)")
    else:
        output.append(f"📊 **找到 {result['returned_count']} 条结果**")
    
    output.append("")  # 空行
    
    for idx, item in enumerate(result["results"], 1):
        output.append(f"**{idx}. {item['title']}**")
        output.append(f"📌 {item['url']}")
        if item.get("content"):
            # 截断过长内容
            content = item["content"][:200] + "..." if len(item["content"]) > 200 else item["content"]
            output.append(f"💬 {content}")
        if item.get("publishedDate"):
            output.append(f"📅 {item['publishedDate']}")
        if item.get("engine"):
            output.append(f"🔧 来源: {item['engine']}")
        output.append("")  # 每条结果后空行
    
    if result.get("suggestions"):
        output.append("💡 **相关搜索**: " + " | ".join(result["suggestions"]))
    
    return "\n".join(output)


# 导出技能
__all__ = ["searxng_search"]