from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select, and_, update
from dependencies.auth_dependencies import get_current_user_dependency
from db.database import get_session
from db.models import (User, Thread, ThreadStatus, ThreadTask, ThreadMessage, ThreadChatType, ThreadChatFromChoices,
                       ThreadTaskStatus, ThreadTaskPlan, ThreadTaskPlanStatus, PlanSubtask, SubtaskStatus, UserType)
from schemas.threads import ListThread, CreateThread, UpdateThread, ListThreadMessage, RetrieveThread, SendMessageObj
from typing import List
from utils.procedures import CustomError, extract_json
from utils import ai_helpers
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from utils import ai_prompts, llm_provider
import json

from utils.default_user import get_default_user


def cleanup_user_working_threads(user_id: str, db: Session):
    """清理用户的所有工作中线程"""
    working_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user_id,
        Thread.status == ThreadStatus.WORKING
    ))).all()

    for thread in working_threads:
        # 取消所有相关任务
        db.exec(update(ThreadTask).where(and_(
            ThreadTask.thread_id == thread.id,
            ThreadTask.status == ThreadTaskStatus.WORKING
        )).values(status=ThreadTaskStatus.CANCELED))

        db.exec(update(ThreadTaskPlan).where(and_(
            ThreadTaskPlan.thread_task.has(ThreadTask.thread_id == thread.id),
            ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE
        )).values(status=ThreadTaskPlanStatus.CANCELED))

        db.exec(update(PlanSubtask).where(and_(
            PlanSubtask.plan.has(ThreadTaskPlan.thread_task.has(ThreadTask.thread_id == thread.id)),
            PlanSubtask.status == SubtaskStatus.ACTIVE
        )).values(status=SubtaskStatus.CANCELED))

        # 删除线程
        thread.status = ThreadStatus.DELETED
        db.add(thread)

    db.commit()


def create_and_execute_single_task(task_text: str, user_id: str, db: Session,
                                   background_mode: bool = False,
                                   extended_thinking_mode: bool = False) -> dict:
    """创建单个任务线程，执行后立即清理"""

    # 1. 清理现有的工作线程
    cleanup_user_working_threads(user_id, db)

    # 2. 分类任务
    llm = llm_provider.get_llm(agent='classifier', temperature=0.1)

    previous_tasks = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread.has(Thread.user_id == user_id),
        ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
    )).order_by(ThreadTask.created_at.desc()).limit(10)).all()

    previous_tasks_arr = []
    for previous_task in previous_tasks:
        previous_tasks_arr.append({
            'task': previous_task.task_text,
            'status': previous_task.status,
        })

    prompt = ChatPromptTemplate.from_messages([
        ('system', ai_prompts.CLASSIFIER_AGENT_PROMPT),
        HumanMessage(f'Previous Tasks (Limited to 10): \n {json.dumps(previous_tasks_arr)}'),
        ('user', task_text),
    ])

    chain = prompt | llm
    response = chain.invoke({})
    response_data = extract_json(response.content)

    # 3. 验证后台模式
    if response_data.get('type') == 'desktop_task':
        if background_mode or response_data.get('is_background_mode_requested', False):
            if response_data.get('is_browser_task') is False:
                raise CustomError(status.HTTP_400_BAD_REQUEST, 'Not_Browser_Task_BG_Mode')

    # 4. 创建临时线程
    thread = Thread(
        title=ai_helpers.generate_thread_title(task_text),
        user_id=user_id,
        current_task=task_text,
        status=ThreadStatus.WORKING if response_data.get('type') == 'desktop_task' else ThreadStatus.STANDBY
    )
    db.add(thread)
    db.flush()  # 获取ID但不提交

    # 5. 添加用户消息
    user_message = ThreadMessage(
        thread_id=thread.id,
        thread_chat_type=ThreadChatType.NORMAL_MESSAGE,
        thread_chat_from=ThreadChatFromChoices.FROM_USER,
        text=task_text,
    )
    db.add(user_message)

    # 6. 添加分类响应
    ai_message = ThreadMessage(
        thread_id=thread.id,
        thread_chat_type=ThreadChatType.CLASSIFICATION,
        thread_chat_from=ThreadChatFromChoices.FROM_AI,
        text=json.dumps(response_data),
    )
    db.add(ai_message)

    response_data['thread_id'] = thread.id

    # 7. 如果是桌面任务，创建任务记录
    thread_task = None
    if response_data.get('type') == 'desktop_task':
        thread_task = ThreadTask(
            thread_id=thread.id,
            task_text=task_text,
            needs_memory_from_previous_tasks=response_data.get('needs_memory_from_previous_tasks', False),
            background_mode=background_mode or response_data.get('is_background_mode_requested', False),
            extended_thinking_mode=extended_thinking_mode or response_data.get('is_extended_thinking_mode_requested', False),
            status=ThreadTaskStatus.WORKING
        )
        db.add(thread_task)



    # 9. 一次性提交所有更改
    db.commit()

    response_data['thread_id'] = thread.id

    return response_data


router = APIRouter(
    prefix='/apps/threads',
    tags=['apps', 'threads'],
)


@router.get('', response_model=List[ListThread])
def list_threads(db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    # 只返回未删除的线程
    query = select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    )).order_by(Thread.created_at.desc())
    return db.exec(query)


@router.post('')
def create_thread(create_thread_obj: CreateThread, db: Session = Depends(get_session),
                  user: User = Depends(get_default_user)):
    """创建并立即执行任务，然后销毁线程"""
    return create_and_execute_single_task(
        task_text=create_thread_obj.task,
        user_id=user.id,
        db=db,
        background_mode=create_thread_obj.background_mode,
        extended_thinking_mode=create_thread_obj.extended_thinking_mode
    )


@router.put('/{tid}')
def update_thread(tid: str, update_obj: UpdateThread, db: Session = Depends(get_session),
                  user: User = Depends(get_default_user)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    instance.title = update_obj.title
    db.add(instance)
    db.commit()
    db.refresh(instance)

    return {'message': 'Success'}


@router.delete('/{tid}')
def delete_thread(tid: str, db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    if instance.status == ThreadStatus.WORKING:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Cannot_Delete_Working_Thread')

    instance.status = ThreadStatus.DELETED
    db.add(instance)
    db.commit()
    db.refresh(instance)

    return {'message': 'Success'}


@router.get('/{tid}', response_model=RetrieveThread)
def retrieve_thread(tid: str, db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    return instance


@router.get('/{tid}/thread_messages', response_model=List[ListThreadMessage])
def thread_messages(tid: str, db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    query = select(ThreadMessage).where(and_(
        ThreadMessage.thread_id == tid,
        ThreadMessage.thread.has(Thread.user_id == user.id),
    )).order_by(ThreadMessage.created_at.asc())
    return db.exec(query)


@router.post('/cancel_all_running_tasks')
def cancel_all_running_tasks(db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    """清理所有用户的工作线程"""
    cleanup_user_working_threads(user.id, db)
    return {'message': 'Success'}


@router.post('/{tid}/cancel_task')
def cancel_running_task(tid: str, db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    if instance.status != ThreadStatus.WORKING:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Not_Running')

    # 直接删除而不是取消
    instance.status = ThreadStatus.DELETED
    db.add(instance)

    # 取消相关任务
    running_task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING
    ))).first()

    if running_task:
        running_task.status = ThreadTaskStatus.CANCELED
        db.add(running_task)

        db.exec(update(ThreadTaskPlan).where(ThreadTaskPlan.thread_task_id == running_task.id).values(
            status=ThreadTaskPlanStatus.CANCELED,
        ))

        db.exec(
            update(PlanSubtask).where(PlanSubtask.plan.has(ThreadTaskPlan.thread_task_id == running_task.id)).values(
                status=SubtaskStatus.CANCELED,
            ))

    db.commit()
    return {'message': 'Success'}


@router.post('/{tid}/send_message')
def send_message(tid: str, obj: SendMessageObj, db: Session = Depends(get_session),
                 user: User = Depends(get_default_user)):
    """发送消息 - 创建新的临时任务执行"""

    # 检查目标线程是否存在（虽然会被立即销毁）
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    # 创建并执行新任务
    return create_and_execute_single_task(
        task_text=obj.text,
        user_id=user.id,
        db=db,
        background_mode=obj.background_mode,
        extended_thinking_mode=obj.extended_thinking_mode
    )


# 新增：批量清理已删除的线程（可选的维护端点）
@router.post('/cleanup_deleted_threads')
def cleanup_deleted_threads(db: Session = Depends(get_session), user: User = Depends(get_default_user)):
    """物理删除所有标记为删除的线程（维护用）"""

    deleted_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.DELETED
    ))).all()

    for thread in deleted_threads:
        # 删除相关消息
        db.exec(select(ThreadMessage).where(ThreadMessage.thread_id == thread.id)).delete()

        # 删除相关任务
        tasks = db.exec(select(ThreadTask).where(ThreadTask.thread_id == thread.id)).all()
        for task in tasks:
            # 删除任务计划
            plans = db.exec(select(ThreadTaskPlan).where(ThreadTaskPlan.thread_task_id == task.id)).all()
            for plan in plans:
                # 删除子任务
                db.exec(select(PlanSubtask).where(PlanSubtask.plan_id == plan.id)).delete()
                db.delete(plan)
            db.delete(task)

        db.delete(thread)

    db.commit()
    return {'message': f'Cleaned up {len(deleted_threads)} deleted threads'}
