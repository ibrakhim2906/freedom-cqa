import json
from pathlib import Path

from .models import Checklist, Criterion, Level
from .settings import ROOT


def official_checklist():
    def binary(cid, title, weight, instruction, na=None, kind="binary"):
        return Criterion(id=cid, title=title, weight=weight, kind=kind,
                         instruction=instruction, na_condition=na, levels=[
                             Level(value="yes", fraction=0 if kind == "flag" else 1, description="Да"),
                             Level(value="no", fraction=0, description="Нет")])

    criteria = [
        binary("contact", "Установление контакта", 10,
               "Да — оператор поздоровался на языке клиента и представился в первом ответе."),
        binary("needs", "Выявление потребности", 15,
               "Да — оператор учёл известные детали и уточнил недостающее до ответа.",
               "Данных для ответа хватало с самого начала."),
        binary("identity", "Идентификация", 20,
               "Да — проверка личности подтверждена до раскрытия данных или защищённого действия. "
               "Если требовалась проверка личности перед защищённым действием и она не подтверждена "
               "в чате, ставьте Нет. Общий вопрос о тарифах не требует идентификации.",
               "Запрос не требовал идентификации."),
        Criterion(id="consultation", title="Корректная и полная консультация", kind="scale", weight=20,
                  instruction="Оцените ответ или следующий шаг. Консультация оценивает, правильно и полно "
                  "ли решён запрос. Ясный ответ на один из двух важных вопросов может получить высокий "
                  "балл за ведение диалога и частичный за консультацию.",
                  na_condition="Чат закончился до того, как клиент сформулировал запрос.", levels=[
                      Level(value="20", fraction=1, description="Все существенные вопросы закрыты или дан корректный следующий шаг."),
                      Level(value="15", fraction=.75, description="Основной вопрос решён, пропущена второстепенная деталь."),
                      Level(value="10", fraction=.5, description="Часть запроса закрыта, существенный вопрос остался открытым."),
                      Level(value="5", fraction=.25, description="Есть общая подсказка, но клиенту всё ещё непонятно, как действовать."),
                      Level(value="0", fraction=0, description="Ответа по существу нет или ключевая рекомендация ошибочна.")]),
        binary("empathy", "Эмпатия и клиентоориентированность", 15,
               "Да — оператор вежлив и, если клиент выразил недовольство или описал неудобство, "
               "отреагировал на конкретную проблему."),
        Criterion(id="management", title="Управление диалогом, скорость и грамотность", kind="scale", weight=15,
                  instruction="Оцените ясность, порядок ответов и предупреждение об ожидании.", levels=[
                      Level(value="10", fraction=1, description="Ответы ясные и связные. Если было явное ожидание, оператор предупредил."),
                      Level(value="7", fraction=.7, description="Один заметный сбой, но клиент может понять ответ и продолжить."),
                      Level(value="4", fraction=.4, description="Клиенту приходится переспрашивать из-за формулировок или порядка ответов."),
                      Level(value="0", fraction=0, description="Из-за бессвязных или противоречивых реплик ход диалога непонятен.")],
                  channel_guidance={"voice call": "Оценивать логичность ведения разговора, понятность объяснений, "
                      "отсутствие неуместных выражений, корректность речевых формулировок и управление паузами. "
                      "Темп, дикцию и произношение оценивать только при наличии анализируемого аудио."}),
        binary("closing", "Завершение", 5,
               "Да — оператор подвёл итог или предложил дальнейшую помощь и попрощался.",
               "Чат оборвался до возможности его завершить."),
        binary("serious", "Грубые ошибки", 0,
               "Да — выявлено оскорбление клиента, предложение платной услуги в обход компании или "
               "раскрытие конфиденциальной информации. Нет — ни одно из трёх не выявлено. "
               "Предложение перевести деньги оператору лично для инвестирования или платной частной "
               "консультации достаточно само по себе: согласие клиента или перевод не требуются.", kind="flag"),
    ]
    return Checklist(id="freedom-chat-quality", version="1", title="Чек-лист качества чатов",
                     instructions=[
                         "Source: CQA_Chat_Quality_Checklist.pdf, pages 1-3; organizer call clarification 2026-11-07.",
                         "N/A разрешён только при выполнении явно указанного условия критерия.",
                         "Для пропущенного действия укажите место, где оно ожидалось. Для N/A объясните условие.",
                         "Порог первой реакции в 3 минуты, теги и вложения в оценку не входят.",
                         "Грубые ошибки отмечаются отдельно и не обнуляют итог.",
                         "Для звонков применяйте аналогичную логику, адаптируя письменную коммуникацию к устной речи."],
                     criteria=criteria)


def load_checklist(path: str | Path | None = None):
    target = Path(path) if path else ROOT / "checklists/freedom-reviewed-012.json"
    return Checklist.model_validate_json(target.read_text(encoding="utf-8"))


def write_official_checklist():
    target = ROOT / "checklists/freedom-v1.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(official_checklist().model_dump(), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return target
