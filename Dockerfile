FROM public.ecr.aws/lambda/nodejs:20

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

COPY package.json package-lock.json ${LAMBDA_TASK_ROOT}/
RUN npm ci --omit=dev \
    && mkdir -p ${PLAYWRIGHT_BROWSERS_PATH} \
    && PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} npx playwright install chromium \
    && PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH} npx playwright install-deps chromium

COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY config.json ${LAMBDA_TASK_ROOT}/config.json

ENV CONFIG_PATH=/var/task/config.json
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

CMD ["src/handler.handler"]
