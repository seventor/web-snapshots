FROM public.ecr.aws/lambda/python:3.12

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt \
    && mkdir -p ${PLAYWRIGHT_BROWSERS_PATH} \
    && PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} playwright install chromium \
    && PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} playwright install-deps chromium

COPY src/ ${LAMBDA_TASK_ROOT}/
COPY config.yaml ${LAMBDA_TASK_ROOT}/config.yaml

ENV CONFIG_PATH=/var/task/config.yaml
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

CMD ["handler.lambda_handler"]
