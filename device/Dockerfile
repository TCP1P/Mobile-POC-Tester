FROM openjdk:18-jdk-slim

WORKDIR /

SHELL ["/bin/bash", "-c"]

RUN apt update && apt install -y --fix-missing curl wget unzip build-essential procps lsof socat
RUN wget https://github.com/firerpa/lamda/releases/download/v8.40/lamda-server-x86_64.tar.gz

ARG ARCH="x86_64"
ARG TARGET="google_apis"
ARG API_LEVEL="31"
ARG BUILD_TOOLS="36.0.0"
ARG ANDROID_ARCH=${ANDROID_ARCH_DEFAULT}
ARG ANDROID_API_LEVEL="android-${API_LEVEL}"
ARG ANDROID_APIS="${TARGET};${ARCH}"
ARG EMULATOR_PACKAGE="system-images;${ANDROID_API_LEVEL};${ANDROID_APIS}"
ARG PLATFORM_VERSION="platforms;${ANDROID_API_LEVEL}"
ARG BUILD_TOOL="build-tools;${BUILD_TOOLS}"
ARG ANDROID_CMD="commandlinetools-linux-13114758_latest.zip"
ARG ANDROID_SDK_PACKAGES="${EMULATOR_PACKAGE} ${PLATFORM_VERSION} ${BUILD_TOOL} platform-tools"

ENV ANDROID_SDK_ROOT=/opt/android
ENV PATH "$PATH:$ANDROID_SDK_ROOT/cmdline-tools/tools:$ANDROID_SDK_ROOT/cmdline-tools/tools/bin:$ANDROID_SDK_ROOT/emulator:$ANDROID_SDK_ROOT/tools/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/build-tools/${BUILD_TOOLS}"
ENV DOCKER="true"

RUN wget https://dl.google.com/android/repository/${ANDROID_CMD} -P /tmp && \
            unzip -d $ANDROID_SDK_ROOT /tmp/$ANDROID_CMD && \
            mkdir -p $ANDROID_SDK_ROOT/cmdline-tools/tools && cd $ANDROID_SDK_ROOT/cmdline-tools &&  mv NOTICE.txt source.properties bin lib tools/  && \
            cd $ANDROID_SDK_ROOT/cmdline-tools/tools && ls

RUN yes Y | sdkmanager --licenses
RUN yes Y | sdkmanager --verbose --no_https --channel=3 emulator && \
    yes Y | sdkmanager --verbose --no_https ${ANDROID_SDK_PACKAGES}

ARG EMULATOR_NAME="pixel_4a"
ARG EMULATOR_DEVICE=$EMULATOR_NAME
ENV EMULATOR_NAME=$EMULATOR_NAME
ENV DEVICE_NAME=$EMULATOR_DEVICE
RUN echo "no" | avdmanager --verbose create avd --force --name "${EMULATOR_NAME}" --device "${EMULATOR_DEVICE}" --package "${EMULATOR_PACKAGE}"

WORKDIR /app
COPY . .

EXPOSE 65000
EXPOSE 60001
ENTRYPOINT ["bash", "./start.sh"]
