from stxnext.staticdeployment.adapters.extraconditions import ExtraDeploymentCondition


class ExampleExtraDeploymentCondition(ExtraDeploymentCondition):
    """
    Example ExampleExtraDeploymentCondition used in tests
    """
    def __call__(self, obj):
      """
      Don't deploy objects with title "Don't deploy"
      """
      if obj.Title() == u'Don\'t deploy':
        return False
      return True
