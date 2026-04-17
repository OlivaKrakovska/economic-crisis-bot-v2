#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления ошибки back_callback в ExpensesConfigView
(без повреждения синтаксиса)
"""

def fix_back_callback(filepath="bot.py"):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Ищем класс ExpensesConfigView
    in_class = False
    in_init = False
    init_end_line = -1
    class_start = -1
    indent_level = ""
    
    for i, line in enumerate(lines):
        if 'class ExpensesConfigView' in line:
            in_class = True
            class_start = i
            indent_level = line[:len(line) - len(line.lstrip())]
            continue
        
        if in_class and 'def __init__' in line:
            in_init = True
            continue
        
        if in_init and line.strip() and not line.startswith(indent_level + "    "):
            # Вышли из __init__
            init_end_line = i
            break
    
    # Проверяем, есть ли уже back_callback
    has_callback = False
    for i in range(class_start, len(lines)):
        if 'def back_callback' in lines[i]:
            has_callback = True
            break
    
    if not has_callback and init_end_line > 0:
        # Добавляем метод после __init__
        callback_method = [
            f"\n{indent_level}    async def back_callback(self, interaction: discord.Interaction):\n",
            f"{indent_level}        if interaction.user.id != self.user_id:\n",
            f"{indent_level}            await interaction.response.send_message(\"Это не ваше меню!\", ephemeral=True)\n",
            f"{indent_level}            return\n",
            f"{indent_level}        await show_expenses_configuration(interaction, self.user_id, self.player_data)\n",
        ]
        
        lines = lines[:init_end_line] + callback_method + lines[init_end_line:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("✅ back_callback успешно добавлен!")
    else:
        print("ℹ️ back_callback уже существует или не найден __init__")

if __name__ == "__main__":
    fix_back_callback()
