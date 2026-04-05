try:
    from models import APIAction, APIObservation, APIState
    print('models OK')
    from client import APIDebugEnv
    print('client OK')
    from tasks.registry import TASK_REGISTRY
    print('tasks OK')
    from graders.grader import APIGrader
    print('grader OK')
    print('ALL IMPORTS PASS')
except Exception as e:
    import traceback
    traceback.print_exc()
