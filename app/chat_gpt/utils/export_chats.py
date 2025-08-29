import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.chat_gpt.dao import ChatDAO, MessageDAO
from app.database import SessionDep, get_session, async_session_maker


def _extract_json_from_chat_html(html_text: str, html_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Надёжно извлекает массив из `var jsonData = [ ... ];`:
    - находим 'var jsonData ='
    - от первой '[' идём символ за символом, пока не закроем все вложенные скобки
    - учитываем строки ('"/'") и экранирование внутри них
    Плюс — запасные варианты (conversations.json и папка conversations).
    """
    # --- 1) Поиск литерала 'var jsonData ='
    marker = "var jsonData"
    i = html_text.find(marker)
    if i != -1:
        # ищем первую '[' после '='
        eq = html_text.find("=", i)
        if eq != -1:
            j = html_text.find("[", eq)
            if j != -1:
                # Сканируем баланс скобок c учётом строк
                depth = 0
                k = j
                in_str = False
                str_quote = ""
                escape = False
                while k < len(html_text):
                    ch = html_text[k]

                    if in_str:
                        if escape:
                            escape = False
                        elif ch == "\\":
                            escape = True
                        elif ch == str_quote:
                            in_str = False
                    else:
                        if ch in ("'", '"'):
                            in_str = True
                            str_quote = ch
                        elif ch == "[":
                            depth += 1
                        elif ch == "]":
                            depth -= 1
                            if depth == 0:
                                # k — индекс последней ']' массива
                                raw = html_text[j:k+1]
                                try:
                                    data = json.loads(raw)
                                    if isinstance(data, list):
                                        return data
                                except json.JSONDecodeError as e:
                                    # Для диагностики, можно посмотреть, что вырезали
                                    # print(f"Decode error at pos {e.pos}: {e}")
                                    pass
                                break
                    k += 1
    # --- 2) Фоллбеки рядом с html (некоторые экспорты кладут JSON-ы отдельно)
    if html_path:
        base_dir = html_path.parent
        conv_json = base_dir / "conversations.json"
        if conv_json.exists():
            data = json.loads(conv_json.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict) and "conversations" in data:
                return data["conversations"]
            if isinstance(data, list):
                return data

        conv_dir = base_dir / "conversations"
        if conv_dir.exists() and conv_dir.is_dir():
            conversations: List[Dict[str, Any]] = []
            for jf in sorted(conv_dir.glob("*.json")):
                try:
                    item = json.loads(jf.read_text(encoding="utf-8", errors="ignore"))
                    if isinstance(item, dict) and "mapping" in item:
                        conversations.append(item)
                except Exception:
                    pass
            if conversations:
                return conversations

    raise ValueError("Не удалось извлечь массив jsonData из chat.html (скобки не сошлись или неизвестный формат).")


def _iter_messages(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Вытаскивает список сообщений (роль + текст) из одного чата"""
    mapping: Dict[str, Any] = conversation.get("mapping") or {}
    items: List[Dict[str, Any]] = []
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue

        role = (msg.get("author") or {}).get("role")
        if role not in ("user", "assistant"):
            continue

        content = msg.get("content") or {}
        if content.get("content_type") != "text":
            continue

        parts = content.get("parts") or []
        text = "\n".join(p for p in parts if isinstance(p, str) and p.strip())
        if not text:
            continue

        items.append({"role": role, "text": text})
    return items


async def main(session: SessionDep, file_path: str):
    # p = Path(r"data_files\file_export\chat.html")
    p = Path(rf"{file_path}")# твой путь
    html_text = p.read_text(encoding="utf-8", errors="ignore")
    conversations = _extract_json_from_chat_html(html_text, html_path=p)
    print("Всего чатов:", len(conversations))

    for conv in conversations:
        title = conv.get("title", "Без названия")

        tg_id = 5254325840
        new_chat = await ChatDAO.create_chat_by_tg_id(session=session, tg_id=tg_id, title=title, project_id=None)

        # print(f"\n=== Чат: {title} ===")
        msgs = _iter_messages(conv)
        for m in msgs:
            role = True if m["role"] == "user" else False
            await MessageDAO.add(session, chat_id=new_chat.id, is_user=role, content=m['text'])
            # print(f"{role}: {m['text'][:50]}")


# --- основной блок ---
if __name__ == "__main__":
    asyncio.run(main())